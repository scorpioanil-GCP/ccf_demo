# 16-23 — the MCP egress door gains a parameterised tool, opt-in

## What did **not** change, stated first

A reader's first question about a change to a shipped door is whether their
door moved. It did not.

- `PRODUCT_URI_TEMPLATE` is the same three segments —
  `ccf-product://{tenant}/{product_class}/{version}` — at the same value.
- The `context_product` **resource handler is byte-identical**: the same
  `verified_grant()` → `entitled_perspective(...)` sequence, the same forwarded
  perspective, the same `request=None` literal and the same
  `canonical_bytes(servable.product).decode("utf-8")` return.
- `request=None` keeps its ruled meaning (`D-IMPL-108`): *this surface carries
  no way to ask*. It is a positive assertion, not a default, and the tool does
  not change what it asserts.
- `ProductResolverProtocol.__call__` is **unchanged** — the same five
  keyword-only arguments, the same types. No entry is filed for it below, and
  that absence is deliberate: a claim on a name that did not move fails the
  completeness gate in the other direction.
- **The tool is opt-in.** A deployment that upgrades and changes nothing gets
  `expose_product_tool=False`, registers no tool, and advertises `tools: []`
  exactly as before. There is no new door without a positive act.

Two tests pin the resource, and they prove different things.
`test_a_verified_entitled_caller_is_served_and_the_allow_is_audited` is
unmodified from before the tool existed, so it is what proves the served bytes
did not move between commits;
`test_registering_the_tool_does_not_move_what_the_resource_serves` builds two
servers from one fixture at this commit, one with the tool and one without, and
compares **raw bytes**, so it is what proves registering a tool does not alter
what the resource returns.

## How this extends `D-IMPL-108` rather than contradicting it

`D-IMPL-126`'s decisive finding about the MCP door as shipped: *which question
gets answered is entirely the server's choice, so the MCP door cannot refute the
reading that a Context Product is a precalculated static object.* A resource with
three path segments and no query surface has no way for a caller to ask
anything, which is precisely why `D-IMPL-108` ruled its request `None`.

So the door now has **two surfaces, deliberately non-overlapping**:

- the **resource** answers *the class's standing answer* — unchanged, and still
  `request=None`;
- the **tool** answers *a question* — whitepaper §6.3's four axes (`subject`,
  `intent`, `freshness`, `asked_at`) carried alongside the same three address
  segments, assembled at the door into a `ProductRequest` before the resolver
  is reached.

The standing-answer case remains the resource. It is **not** a tool call with
four `None`s, because there is no such call: all four axes are required by the
tool's input schema, which makes a partial address *unrepresentable* rather than
refused. That is strictly stronger than the HTTP door's some-but-not-all
refusal, which exists only because query parameters are individually omittable.

## The seam was already wide enough

`D-IMPL-108` and plan `15.5-15` widened `ProductResolverProtocol` from three
arguments to five across 24 files, once, *specifically so it would never be
widened again*. This change collects on that: **zero resolver call sites move,
no Protocol signature changes, and nothing under `src/` is touched.** The tool
calls the same five-argument seam the resource calls, differing only in passing
a `ProductRequest` where the resource passes `None`.

## The tool is narrower than the resource, not wider

Stated because a second door onto the same assembly is exactly where a widening
hides:

- **No `role` parameter.** The tool passes `requested_role=None`, as the
  resource does, and lets the deployment's resolver derive the role from the
  verified grant.
- **No caller-supplied `schema_name` or `schema_version`.** Both are bound to
  the handler's own `product_class` and `version` arguments — the values the
  entitlement decided on — so a request addressed to another class cannot be
  expressed on this surface at all.
- **No `parameters`.** The empty mapping, for the reason
  `http_api/routes/product.py` already records: a flat tool-argument map cannot
  carry `D-IMPL-103`'s declared nested types without the door guessing at
  coercions. See *Adopter migration* for the measured consequence.
- **Same governance, same order.** The identical `verified_grant()` →
  `entitled_perspective(...)` call, and the perspective it returns is **bound
  and forwarded** rather than re-derived — `DI-15.5-03` is the recorded defect
  of a door that resolved an entitled perspective and discarded it, and a new
  door is where it would come back. A parametrized in-process matrix asserts
  both surfaces agree on all seven governance scenarios from one server, one
  policy and one grant, and a separate test asserts the forwarded perspective
  **by value**, because outcome parity is blind to a fabricated one.

## Adopter migration

**To open the door**, pass both arguments together:

```python
server = build_egress_server(
    server_name=...,
    resolver=...,
    token_verifier=...,
    auth_settings=...,
    entitlement_source=...,
    perspective_resolver=...,
    expose_product_tool=True,
    product_tool_description="…what your consumers should read…",
)
```

Either argument without the other raises `ValueError`. Two arguments rather than
one is deliberate: *is this door open?* must be answerable by grepping for a
boolean, never inferred from whether a prose string happened to be supplied. The
SDK ships **no** default description — the words your consumers read are yours
(CINV-01).

**The measured constraint, and it will bite before anything else does.** The
tool sends `parameters={}`, so a product class whose request contract declares
**any required parameter** is not reachable through it. Against the committed
`examples/s1-01` contract this reads, verbatim:

```
reason='missing-required-parameter' key='decision_instant'
```

The HTTP door has the identical property today. A class intended to be reachable
through either parameterised door must declare no *required* request parameters;
optional ones are fine. This is recorded as residual (b) below, not solved here.

**A timezone-naive `asked_at` is refused at the door** with
`NaiveAskedAtRefused`, citing `D-IMPL-38`. `ProductRequest` accepts a naive
instant and the failure would otherwise surface later inside `canonical_bytes`,
turning a client's malformed argument into an opaque server error and an
unpinnable replay record. Send an offset.

## Residual (a) — client-chosen `subject` is not entitlement-scoped

**Ruled: `D-IMPL-128` limb 2 (RESOLVED, Dave, 2026-08-13). This is a named
residual under an existing ruling, not a candidate for one.**

`entitled_perspective` decides on `(grant, tenant, product_class, resolved
role)` and carries **no subject dimension**
(`runtime/ccf_runtime/authz/product_entitlement.py::entitled_perspective`),
while `subject`
becomes the traversal seed (`request_seeds`, `D-IMPL-111` limb (a)) and
therefore selects what is assembled.

**The delta this tool introduces is zero, and that is a measurement rather than
an argument.** Anything reachable as `call_tool(subject=S)` is already reachable
as `GET /product/{tenant}/{class}/{version}?subject=S&…` on the same grant,
through the same decision, on a door shipped since `D-IMPL-108`
(`runtime/ccf_runtime/http_api/routes/product.py::build_router`). The tool
widens the vocabulary of doors, not the set of reachable state.

Closing it needs a **perspective-scoped assembly path that does not exist**:
`D-IMPL-119` limb 2 measured the entitled-versus-assembled delta as *empty on
the shipped path* and put the scoped view out of scope, and `D-IMPL-124` Shape D
was **blocked** on the same absence.

**Unassigned by ruling.** The trigger for opening it is a concrete harm or an
authorised scoped-assembly workstream. Carried verbatim from limb 2: *no plan
may cite the tool's shipping as evidence that subject-scoping is unnecessary.*

## Residual (b) — a class declaring any required request parameter is unreachable

**Attaches to `D-IMPL-113`**, which records the seam this is blocked behind.

Measured at this commit against the committed `s1-01` request contract:
`parameters={}` yields `reason='missing-required-parameter'
key='decision_instant'`. The HTTP door has the identical property.

The obvious repair — carry the class's declared parameters — is blocked by the
same seam `D-IMPL-113` records: validating them needs the
`RegisteredProductClass`, which **the door never holds**; it is resolved behind
the resolver seam. The SDK cannot call a comparison whose second operand it does
not have.

**Consequence for `D-IMPL-127`'s HW-1/HW-2 pair**, which is where this becomes
load-bearing rather than notional: HW-2 is required to change only the *client*,
so HW-1's product class must declare **no required request parameters**, or
`decision_instant` must stop being one.

**Owner: the HW-1 plan.** It is a design constraint on that plan rather than a
defect in this one.

## Residual (c) — `get_context` is authenticated but not entitled (cross-reference)

**Already ruled and already owned. This is a cross-reference, not a discovery.**

`runtime/ccf_runtime/mcp/experience.py::build_experience_server`'s
`get_context` takes both arguments from the client and calls neither
`verified_grant()` nor `entitled_perspective(...)`, while the
`context_product` resource on the same server calls both. `D-IMPL-128` limb 1
(RESOLVED, Dave, 2026-08-13) rules it a defect and orders it *"fix it in this
phase"*; `D-IMPL-129` assigns `get_context` and `get_lineage` to plan
**`16-24`**, whose `files_modified` includes `experience.py`.

`D-IMPL-128` names *this* plan's tool under **Governs** as the door that
deliberately does **not** copy that shape, and the reason a reviewer will ask
for is worth keeping in view: the precedent `D-IMPL-126` cites proves a
parameterised MCP tool is *buildable*, not that it is *governed*. `D-IMPL-128`
records that framing itself, and records that this plan's own security analysis
is how the defect was found — *"no audit and no lint found it."*

No candidate `D-IMPL` id is filed for it, and it is not recorded as unruled or
unowned.

## ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL

- Surface: ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL
- Public surface: true
- Before: absent
- After: a module-level `str` constant naming the one parameterised Tool this
  server can register, exported in `__all__`. Named once here rather than at
  each use site for the reason `product_uri` exists: the server, the tests and
  the docs must agree what the surface *is* rather than each spelling it
- Change type: added
- Why: `D-IMPL-126` item 5. A tool name repeated as a literal at the
  registration, in every test and in the docs is three places to drift; the
  resource address already solved this with `product_uri`
- Migration: none — new name. Read the tool's name from this constant rather
  than hard-coding the string, so a rename reaches your call sites

## ccf_runtime.mcp.egress.NaiveAskedAtRefused

- Surface: ccf_runtime.mcp.egress.NaiveAskedAtRefused
- Public surface: true
- Before: absent
- After: a named `ValueError` subclass raised as the **first statement** of the
  product tool's body when `asked_at` carries no UTC offset, before any
  governance seam is consulted. Exported in `__all__`
- Change type: added
- Why: `ProductRequest` *accepts* a naive instant and the failure surfaces later
  inside `canonical_bytes` (`D-IMPL-38`), which would convert a client's
  malformed argument into an opaque server error and an unpinnable replay
  record — `asked_at` is the boundary a replay resolves against. A **named**
  subclass rather than a bare `ValueError` follows the shipped
  `ccf_runtime.mcp.hitl_server.NaiveActionTimeRefused` precedent, so a
  deployment can catch this specific refusal. It is a `ValueError` rather than a
  typed `ERROR_*` code because it is a malformed argument and not a governance
  decision — the same line `NaiveActionTimeRefused` sits on, and not an
  inconsistency with `D-08`
- Migration: none — new name. If you call the tool, send a timezone-aware
  `asked_at`; if you wrap the door, `except NaiveAskedAtRefused` distinguishes a
  malformed instant from an entitlement refusal

## ccf_runtime.mcp.egress.build_egress_server

- Surface: ccf_runtime.mcp.egress.build_egress_server
- Public surface: true
- Before: six required keyword-only arguments — `server_name`, `resolver`,
  `token_verifier`, `auth_settings`, `entitlement_source`,
  `perspective_resolver`
- After: the same six, unchanged and still required, plus two keyword-only
  arguments **both defaulting closed**: `expose_product_tool: bool = False` and
  `product_tool_description: str | None = None`. Supplied together or not at
  all — either without the other raises `ValueError` naming both, in the `D-03`
  requiredness-conditional-on-exposure voice. With the pair supplied the builder
  registers exactly one Tool, named by `PRODUCT_REQUEST_TOOL`, whose advertised
  `inputSchema` requires exactly `tenant`, `product_class`, `version`,
  `subject`, `intent`, `freshness` and `asked_at` and carries no `role`, no
  `schema_name`, no `schema_version` and no `parameters`. The resource, the URI
  template and the resolver Protocol are untouched
- Change type: reshaped
- Why: `D-IMPL-126` item 5, gating HW-2 in `D-IMPL-127`. A resource-only door
  cannot refute the reading that a Context Product is a precalculated static
  object, because a caller with no way to ask a question cannot demonstrate that
  the answer depends on one. Opt-in rather than on-by-default because a
  deployment that reviewed and approved a resource-only door must not acquire a
  parameterised authorization surface it never assessed merely by upgrading —
  deny-by-default, this module's stated posture, applied to exposure. Two
  arguments rather than one because *is this door open?* must be answerable by
  grepping for a boolean. No `DEFAULT_*` description constant ships, unlike the
  Experience server's tools: the prose an adopter's consumers read is not the
  SDK's to write (CINV-01)
- Migration: **none required.** Every existing call site keeps working
  unchanged and registers no tool, which is the whole point of the default. To
  open the door, pass `expose_product_tool=True` **and**
  `product_tool_description="…"` together; see *Adopter migration* above,
  including the measured constraint that a class declaring any required request
  parameter is not reachable through the tool
