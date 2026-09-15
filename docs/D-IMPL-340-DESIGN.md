# D-IMPL-340 — design package (RULED direction B; IMPLEMENTATION GO 2026-09-14)

**Baseline: `main` @ `c635037f`.** Branch `d-impl-340-cross-deployment`;
implementation candidate **`4c822611`** (see §14 for what was built as designed
and where the build departed from this package). CP-14 Gate 2 is HOLD
throughout; no merge without Dave's review.

Every measurement here was taken on the baseline; the two probes are described
in `docs/DECISIONS.md` under `D-IMPL-340` and reproduce from the fixture wiring
of `tests/products/composite_fixture.py::build_composite`.

---

## 0 · The ruling this package serves (Dave, 2026-09-14)

- **Reading B, with one identity refinement.** A is rejected (the five frozen
  products are independently deployed; `D-IMPL-261` stands). C is rejected as
  the architectural answer (running every producer against one store and one
  register demonstrates nothing about cross-deployment composition).
- **Two capabilities.** (A) *Parameterized cross-deployment acquisition* — a
  granted skill asks a **registered** remote producer a question and receives
  the governed product answering it, through the producer's **existing**
  parameterized surface (`request_context_product`); arguments actually reach
  the producer; nothing is interpolated into a network address; the logical
  MCP server registry and its SSRF posture stay in force; no producer assembler
  enters the consumer process. (B) *Cross-deployment child admission* — the
  rule is **not** `composite tenant != child tenant`. Admission distinguishes
  the consumer tenant, the **expected producer identity**, the **tenant under
  which the child was governed**, the product class/version, and the provider
  relationship / eligibility authority. Expectations derive from **governed
  deployment / grant / binding state**, never solely from fields in the
  returned child; a payload cannot authorize itself by claiming them. For a
  remote MCP producer, eligibility stays `provider-controls`, the local
  invalidation register is neither consulted nor credited, and replay records
  which producer supplied the child and the producer-side tenant/governance
  context. Same-fabric / local-dispatch semantics are unchanged. Peering stays
  conceptually consistent and is not rewritten here.
- **`requires:` stays about the product.** A composite declares the exact
  class/version it consumes — never an implementation, a skill, a business
  label, or "anything that could answer a similar question". `produces:` and
  the granted binding decide *how* that class is obtained. **No producer
  identity is added to `ChildRequirement`.**

The flow, unchanged in shape and now real end to end:

    requirement → granted skill → registered producer binding
                → parameterized request → governed child → admission

---

## 1 · What is missing today, stated as three measured facts

1. **No transport carries a question to a producer outside this fabric.**
   `_invoke_local_callable` passes arguments but presumes this fabric's store
   and register; `_invoke_mcp` reads the one URI `McpSkillRegistry.register`
   mapped for the binding and only *records* `arguments`; `_invoke_peering`
   drains `transport.receive()`. (`src/ccf/skills/dispatch.py`.)
2. **The composite's request never reaches the child mapping.**
   `GovernedResolver` calls the child resolver with `requirements, asked_at,
   admitted_at, composition_invocation, consumer_lineage`; `ChildArguments` is
   `Callable[[ChildRequirement, datetime], Mapping[str, str]]`. A per-request
   anchor reaches a child only by closing over state outside the declared
   mapping. (`src/ccf/products/resolver.py:1991`, `child_resolver.py:120`.)
3. **The gate admits one tenant.** `CompositeAdmissionGate.admit` check 1 is
   `contract.tenant_id != self._tenant_id → tenant-mismatch`; the peering gate
   applies the same rule. A child governed under its producer's own tenant is
   refused on every transport. Measured: cp-04-canonical → `tenant-mismatch`;
   with the tenant matched and the requirement corrected → `AdmittedChild`.

What already exists and is reused unchanged: the producer's parameterized
door (`runtime/ccf_runtime/mcp/egress.py::request_context_product`, with
`verified_grant` → `govern_entitlement` → `door_answer`), `DoorOutcome`,
`McpSkillRegistry`'s *name-not-address* posture, `McpResourceClient` and its
bridge, `ResolvedProducer` / `ChildInvocation` minting, `CompositeAdmissionGate`
checks 2–7, `ChildResolution` rows, `ADMITTED_CHILD_CONTRACT_CLASS` retention
and `CompositeReplayEnvironment` (`D-IMPL-339`).

---

## 2 · Producer identity model

Five things, kept apart, each with one source of truth:

| Concept | Source of truth | Where it lives | Who may write it |
| --- | --- | --- | --- |
| **Consumer tenant** | the composite's own fabric | `CompositeAdmissionGate.tenant_id` | the deployment, at boot (unchanged) |
| **Expected producer identity** | a **producer registration** | `ProducerRegistration.producer_id` (+ the endpoint and credential *names* it is reached by) | the composition root, from a Control Plane artifact (§3) |
| **Expected producer-side tenant** | the same registration | `ProducerRegistration.producer_tenant` | same |
| **Tenant the child was governed under** | the returned child | `contract.tenant_id`, and the tenant segment of `DoorOutcome.replay_ref` | the producer — a **claim**, verified against the two rows above |
| **Provider relationship / eligibility authority** | the dispatch result's **type** | `ChildInvocation.acquisition` → `eligibility_basis` | machinery only (`invocation_from_dispatch`, unchanged rule) |

**Identity is the registration, not the answer.** The consumer knows, without
trusting anything on the wire, *which registration it resolved* — the grant's
binding names a logical server, the registry maps it to one client built at
the composition root, and an unregistered name is refused before a socket is
opened (T-06-24, unchanged). That resolved registration is the expected
producer identity. The returned child is then held to it: its governing tenant
must equal `producer_tenant`; its `replay_ref` must sit under that tenant; and
where the door asserts a producer (§4.3) the assertion must equal
`producer_id`. **Equality never authorizes** — the grant plus the registration
authorized the acquisition before any bytes arrived; equality only confirms
the bytes came from the producer the registration names, and *inequality
refuses*. That is what makes proofs 3, 4, 5, 6 and 7 (§10) distinct tests
rather than one.

**Why `producer_id` is a registration value rather than a signature.** MCP
authentication in this SDK is client→server (D-26 bearer tokens verified by
the producer; `runtime/ccf_runtime/mcp/auth.py`). The producer does not sign
its answers, and this package does not introduce a second PKI: peering already
owns signed producer attestation (`ccf.peering.identity`, trust policy
`permitted_producer_hashes`), and a deployment that needs a *signed* producer
identity has that transport. For MCP the producer's identity is established the
way its endpoint is: as deployment configuration the composition root loads.

---

## 3 · Producer-side tenant / governance binding — the registration artifact

A new Control Plane artifact class, **`ccf.mcp-producer`**, one per remote
producer a deployment is willing to ask. Declared, versioned, content-hashed,
loaded at boot into the registry — so the expectations admission checks are
**governed state** (proofs 3 and 4).

```yaml
# artifacts/producer-<name>.yaml   ($schema=…/ccf.mcp-producer.json)
class_id: ccf.mcp-producer
semver: "1.0.0"
declaration:
  server: exposure-rollup-producer        # the logical name McpProductBinding selects
  producer_id: cp-05-egress               # expected producer identity (a name, not an address)
  producer_tenant: cp-05-demo             # tenant the producer governs under
  endpoint_from_env: CCF_CP_14_PRODUCER_EXPOSURE_URL      # an env-var NAME (CINV-01); never a URL
  credential_from_env: CCF_CP_14_PRODUCER_EXPOSURE_TOKEN  # an env-var NAME; never a token
  offers:                                 # what this producer may be asked for
    - product_class: credit-risk.exposure-rollup
      versions_from: "1.0.0"              # same caret-shaped rule as ChildRequirement
```

Rules the artifact enforces (validators, `extra=forbid`):

- `endpoint_from_env` / `credential_from_env` are **names**. A literal URL,
  host, port or token in the artifact is refused at parse. The No-Hardcoding
  lint gains the same check for `ccf.mcp-producer` documents.
- `offers[].product_class` must be unique within one registration.
- `producer_tenant` may equal the consumer's tenant (a same-tenant remote
  producer is the crossproc fixture's case) — but it is **always declared**,
  never defaulted to the consumer's.

Boot: the deployment loader (`src/ccf/deployment/config.py`, a new reserved
section `producers:` → `ccf.mcp-producer`, list-valued like `half_life`) reads
the two env-var names, builds `McpResourceClient(url=<env>,
http_client_factory=<bearer from env>, bridge=<deployment's>)` and calls
`McpSkillRegistry.register_producer(...)`. **This is the only place a URL or
a token is resolved**, and it is deployment configuration exactly as it is for
the artifact server today (`ccf.mcp.client` docstring, CINV-01).

`ProducerRegistration` (frozen dataclass, module-private constructor on the
`BoundSkillView` precedent, WR-03):

```python
@dataclass(frozen=True)
class ProducerRegistration:
    server: str
    producer_id: str
    producer_tenant: str
    offers: tuple[ProducerOffer, ...]     # (product_class, versions_from)
    artifact_address: str                 # content hash of the ccf.mcp-producer document
```

`artifact_address` is what replay records as the governance context of the
acquisition (§7): *this* registration, at *this* content, authorized asking
*this* producer.

---

## 4 · Parameterized request flow (capability A)

### 4.1 · The skill side: a product-request binding

A **sixth skill type**, `mcp_product`, and its binding:

```python
class McpProductBinding(CCFContract):
    server: str            # selects a ProducerRegistration by logical name
    product_class: str     # what is asked for — must equal the entry's `produces`
    product_version: str   # the lane the producer is asked at
```

- `SkillType` gains `"mcp_product"`; `_BINDING_CONTRACTS["mcp_product"] =
  McpProductBinding`; `docs/schemas/ccf.skill-catalog-entry.json` gains the
  enum member and the binding shape. `McpBinding` (fixed resource) is
  **untouched** — existing `mcp` entries keep reading the resource they always
  read (proof 13 covers this leg too).
- Validator: `produces == binding.product_class` for `mcp_product`. A skill
  that says it produces X while asking for Y is refused at registration, not
  at admission.
- Why a new type rather than a second shape under `mcp`: the audit record
  carries `artifact_class=entry.skill_type`, `invocation_from_dispatch` binds
  the acquisition kind to the entry's type, and a reader of the catalog should
  see at a glance which entries can *ask* and which can only *read*.

### 4.2 · The question: what reaches the producer, and from where

Every argument of `request_context_product` has exactly one authoritative
source. None may be overridden by the mapping the deployment writes:

| Tool argument | Source | Never from |
| --- | --- | --- |
| `tenant` | `ProducerRegistration.producer_tenant` | the child mapping, the parent request |
| `product_class`, `version` | `McpProductBinding` (which the validator tied to the requirement's class via `produces`) | the mapping |
| `asked_at` | the composite's `request.asked_at` — the one reconstruction instant | the mapping |
| `subject`, `intent`, `freshness`, `parameters` | the **child question mapping** (§4.4) | — |
| `request` | the canonical `WireRequest(product_id=product_class, parameters=…, temporal_boundary=asked_at)` the consumer builds | the mapping |

The consumer keeps the `WireRequest` it sent. The producer echoes it in
`DoorOutcome.request` (existing contract), and admission refuses an answer
whose echo differs from what was asked (§6, `question-mismatch`). That is the
binding between *this* question and *this* product — the property proof 1
measures with two argument sets.

### 4.3 · Dispatch and the door

`dispatch_skill` gains one branch:

```python
if isinstance(binding, McpProductBinding):
    return _invoke_mcp_product(entry, binding, question, mcp_skills=mcp_skills)
```

`_invoke_mcp_product` resolves `(client, registration) =
mcp_skills.resolve_producer(binding)` — refusing, before any network, a server
that is unregistered **or** whose `offers` do not include the binding's class
at a compatible lane (`ProducerDoesNotOffer`, an exception like
`McpSkillUnregistered`: wiring, not governance). It then calls
`client.call_tool_text(PRODUCT_REQUEST_TOOL, arguments)` — a new primitive on
`McpResourceClient` beside `read_text`, same bridge, same deadline, same
`http_client_factory` (so the D-26 bearer token rides as it does for every
other read). The result is:

```python
class McpProductInvocation(CCFContract):
    skill_name: str
    skill_type: str                  # "mcp_product"
    server: str
    producer_id: str                 # copied from the registration the registry resolved
    producer_tenant: str             # same
    producer_registration_address: str
    product_class: str
    product_version: str
    question: WireRequest            # what was sent
    contents: str                    # the DoorOutcome JSON the producer returned
    arguments: Mapping[str, str]     # audit copy, as today
```

The registration values on the invocation are **copied by the registry at
resolution**, the way `ResolvedProducer` copies the grant hash from the ledger:
a caller cannot construct an invocation naming a producer the registry did not
resolve, because `dispatch_skill` is the only constructor path that runs and
`invocation_from_dispatch` refuses an object whose type and `skill_type`
disagree (existing check, extended to the new type).

**Producer assertion on the door (egress-side, optional but recommended).**
`DoorOutcome` gains `producer: ProducerAssertion | None = None` —
`(producer_id, tenant_id)` — stamped by `build_egress_server` from the values
the deployment already passes it (`server_name`, the resolver's tenant).
Additive and `None` for every existing door and every existing test. The
`mcp_product` admission leg **requires** it (`producer-unasserted` refusal),
and holds it equal to the registration (`producer-mismatch`). This is what
gives proof 5 an observable distinct from proof 6, and it is a *consistency*
check, not an authorization: the registration was the authority before the
assertion arrived, and the assertion can only cause a refusal.

### 4.4 · The child question mapping — the composite's request reaches the child

Replace the closed-over-state workaround with a declared mapping that receives
the composite's **effective** request (defaults applied, policy narrowed — the
same authority chain every other argument travels, `D-IMPL-302`):

```python
class ChildQuestion(CCFContract):
    subject: str
    intent: str
    freshness: str
    parameters: Mapping[str, WireParameterValue]   # the WireRequest value grammar, unchanged

ChildQuestions = Callable[[ChildRequirement, ProductRequest], ChildQuestion]
```

`GrantBoundChildResolver` takes `child_questions=` **instead of** (mutually
exclusive with) `child_arguments=`; a resolver constructed with both, or
neither, is refused. The legacy `child_arguments` path is unchanged for
existing callers.

**Reaching the resolver:** `CompositeChildResolverProtocol.__call__` is not
widened — Dave's rule, *"adding a defaulted parameter to a Protocol does not
make existing implementations accept that keyword"*, and the
`EvidenceAwareFactorScorer` / `CompositePlanFactoryProtocol` precedent. A
**capability Protocol**:

```python
@runtime_checkable
class RequestAwareChildResolverProtocol(Protocol):
    def resolve_for(self, *, requirements, request: ProductRequest, asked_at,
                    admitted_at, composition_invocation, consumer_lineage) -> dict[str, object]: ...
```

`GovernedResolver` at the acquisition site (`resolver.py:1991`):

```python
if isinstance(self.composite_children, RequestAwareChildResolverProtocol):
    outcomes = self.composite_children.resolve_for(..., request=effective_request, ...)
else:
    outcomes = self.composite_children(...)          # byte-identical legacy call
```

Structural `isinstance`, no `TypeError` probing, no defaulted keyword. A
`GrantBoundChildResolver` built with `child_questions` declares the capability;
one built with `child_arguments` does not, and takes the legacy call.

The mapping's output can only populate the four question fields. `asked_at`,
`tenant`, `product_class`, `version` and the endpoint are not reachable from
it — **no request argument can become a network address** (proof 12) because
there is no code path from `ChildQuestion` to a URI: the tool call takes a
structured argument object, and the `/q/{q}` addressed-resource form is
deliberately **not** used by the consumer.

---

## 5 · Registry, dispatch and client changes — the exact surface delta

| Module | Change | Compatibility |
| --- | --- | --- |
| `ccf.skills.catalog` | `SkillType` + `"mcp_product"`; `McpProductBinding`; `_BINDING_CONTRACTS` entry; `produces == product_class` validator | additive; existing entries unchanged |
| `ccf.skills.dispatch` | `McpSkillRegistry.register_producer(*, client, registration)`, `resolve_producer(binding) -> (client, registration)`; `McpProductInvocation`; `_invoke_mcp_product`; `ProducerDoesNotOffer` | `register`/`resolve`/`_invoke_mcp` byte-identical |
| `ccf.mcp.client` | `McpResourceClient.call_tool_text_async(name, arguments)` / `call_tool_text` — one `session.call_tool`, text content joined as `read_text` joins resource contents; same bridge, deadline, factory | additive |
| `ccf.products.door` | `ProducerAssertion`; `DoorOutcome.producer: ProducerAssertion \| None = None` | additive, default `None` |
| `ccf_runtime.mcp.egress` | `build_egress_server` stamps `producer` on both tool branches (served and refused) | additive; resource surface untouched |
| `ccf.products.composite` | `ChildAcquisition` + `"mcp-product"`; `_ACQUISITION_OF["McpProductInvocation"] = ("mcp-product", "mcp_product")`; `ChildInvocation` carries `producer_id`, `producer_tenant`, `producer_registration_address` (from the invocation, machinery-copied); gate: producer leg (§6); `RequestAwareChildResolverProtocol`; new refusal reasons | existing legs byte-identical |
| `ccf.products.child_resolver` | `ChildQuestion`, `ChildQuestions`, `child_questions=` constructor arg; `resolve_for`; `_admit` branch for `McpProductInvocation` (no store read, like `mcp`) | `child_arguments` path unchanged |
| `ccf.products.resolver` | the `isinstance` branch at the acquisition site | legacy call unchanged |
| `ccf.deployment.config` | reserved section `producers:` → `ccf.mcp-producer` (list) | additive |
| `ccf.controlplane.artifacts` | `ccf.mcp-producer` declaration + validators | additive |
| `ccf.replay.record` | `ChildResolution` fields (§7) | additive, `None` defaults |
| `ccf.contracts.guarded` | registry rows for `ProducerRegistration` (mint: `register_producer`) and the `McpProductInvocation` consumer boundary, per `D-IMPL-337` | lint-enforced |
| `tools/lints/no_hardcoding` | `ccf.mcp-producer` may carry no literal URL/host/port/token | new check |

Nothing in `src/` imports a harness or a producer's code. The consumer process
holds a client, a registration and an admission gate — proof 2 is a
module-population assertion over `sys.modules` after a real acquisition.

---

## 6 · Admission changes (capability B)

`CompositeAdmissionGate.admit` keeps its seven checks and its order for the
existing legs. It gains a **producer leg** selected by
`candidate.invocation.acquisition == "mcp-product"`, run **in place of check 1**
(the tenant check) and **before** check 2:

| # | Check | Refusal |
| --- | --- | --- |
| 1p | `contract.tenant_id == invocation.producer_tenant` | `producer-tenant-mismatch` |
| 1p′ | `replay_ref` is `ccf-artifact://<producer_tenant>/…` (tenant segment of the parsed URI) | `producer-tenant-mismatch` |
| 1q | `DoorOutcome.producer` present | `producer-unasserted` |
| 1q′ | `DoorOutcome.producer == (producer_id, producer_tenant)` from the invocation | `producer-mismatch` |
| 1r | `DoorOutcome.request == question sent` (subject, parameters, temporal boundary) | `question-mismatch` |
| 2–6 | class, version lane, `temporal_boundary == asked_at`, recomputed address, assessable debt | unchanged |
| 7 | eligibility: `mcp-product` → `(ELIGIBILITY_PROVIDER_CONTROLS, None)`; the local register is **not** consulted, `touched_entities` is `None` and its supply is refused by `invocation_from_dispatch` as for `mcp` | unchanged shape |

Where the expectations come from is the whole point of 1p/1q: `producer_tenant`
and `producer_id` on the invocation were copied from the registration the
registry resolved for the grant's binding. The candidate's contract and door
outcome contribute only *claims*; a claim that matches merely fails to refuse.

**`ChildRefusalReason`** gains `producer-tenant-mismatch`, `producer-mismatch`,
`producer-unasserted`, `question-mismatch`, `producer-unavailable` (§8). Each
is emitted on exactly one path and has a sabotage (§11) — `CP14-F-10` recorded
three declared-but-unreachable tokens; this package adds none of that kind.

**Local dispatch (`local-dispatch`)**: check 1 stays
`contract.tenant_id == gate.tenant_id`; eligibility stays `local-register`
with `touched_entities` from the child's own record. **Fixed-resource `mcp`**:
unchanged, including its consumer-tenant check — that leg is a same-tenant
remote read and nothing in this ruling asks it to change. **Peering**: §9.

**Why the tenant check is replaced rather than relaxed.** A single rule
`child.tenant ∈ {consumer, producer}` would let a producer-tenant child arrive
through a same-tenant registration, or vice versa, and admit either. The
expectation is per acquisition kind and per registration, and each leg checks
the one thing it can know.

---

## 7 · Replay fields and evidence

`ChildResolution` (five-dimension record, dimension 4 rows) gains, all
`None`-defaulted so every existing row and every existing reader is
unchanged:

| Field | Value on an `mcp-product` row | Source |
| --- | --- | --- |
| `producing_fabric` (existing) | `producer_id` | the registration the registry resolved (today: the verified peer for `peered`, `None` for `mcp`) |
| `producer_tenant` | `producer_tenant` | same |
| `producer_registration_address` | content hash of the `ccf.mcp-producer` document | same |
| `producer_server` | the logical server name | the binding |
| `child_replay_ref` | the producer's replay-record URI, as returned | the door outcome, **retained as the producer's claim** and labeled so — the consumer never resolves it (Dave: *"do not require access to a remote provider's internal replay store"*) |
| `child_question_address` | content hash of the `WireRequest` sent | the consumer |
| `eligibility_basis` (existing) | `provider-controls` | machinery |

Retention: admitted contracts continue to be filed under
`ADMITTED_CHILD_CONTRACT_CLASS` by exact content address (`D-IMPL-339`), so
`replay()` rebuilds the `ChildContractView` from bytes and makes **no producer
call** — the 339 one-shot-door proof is re-run against a producer whose process
has been stopped (proof 11 and the replay half of the CP-14 `CMC-G29`
obligation). The row answers, from the record alone: *which producer, under
which tenant, authorized by which registration and grant, supplied which child,
answering which question* — Dave's "replay identifies the exact producer and
admitted child".

Audit: `McpSkillRegistry.record_invocation` is called on both outcomes as
today; the record's `artifact_class` is `mcp_product`, which is how an
operator distinguishes an ask from a read in the audit plane.

---

## 8 · Refusal behavior

Three outcomes, three shapes — the refusal-vs-exception line the SDK already
draws (*"refusals are values; a misused state machine is an exception"*):

1. **The producer refused, governed.** `DoorOutcome.refusal` is a disclosed,
   replay-referenced `RefusalEnvelope`. Today's rule holds: the row is
   `ineligible` with detail *"the child's own door refused: <kind>"* and
   `refusal_ref` = the child's replay reference; a required slot refuses the
   composite before projection with every row (`D-IMPL-338`/`339`).
2. **The producer failed, opaquely.** The tool raised `ToolError` carrying
   `ccf-runtime-failure:<id>` (`D-IMPL-253` Q20), or an entitlement denial
   rendered as the protocol-native error, or the transport timed out /
   was unreachable (`McpClientError`). **Proposed: a governed refusal, not an
   exception.** Row `producer-unavailable` with the opaque id or error class
   in `detail`, the composite refuses the required slot with its rows, and a
   replay record exists for the refusal. Rationale: an unreachable producer
   during *this* composition is a fact about this decision's evidence, which
   Dave's stop conditions want visible as a refusal with rows, not as a stack
   trace. **Contrast, kept:** an *unregistered* server or a producer that does
   not *offer* the class stays an exception (`McpSkillUnregistered`,
   `ProducerDoesNotOffer`) — the deployment is mis-wired, and no decision was
   made. This is the one item in §8 that changes a posture and it is flagged
   for Dave's ruling in §12.
3. **The producer answered something else.** Wrong tenant / producer /
   question / class / lane / instant / address — the §6 refusals, each a row.

`F-21` (a missing anchor **raised** by 16 of 19 shipped trees instead of
refused) is a **producer-side** population finding and is **not** folded in
here; from the consumer's side a raised producer is case 2 and is refused as
`producer-unavailable`. The producer-side repair is a separate finding
(`CP14-F-21`, its census in `CP-SPEC-014` §F.2).

---

## 9 · Compatibility with peering — and one semantic divergence, recorded

Peering's model is unchanged: a peer's product is signed; the trust policy's
`PeerTrustGrant` says which `producer_agent_definition_hash`es, schema names
and policy regimes that peer may assert; the admission gate verifies the
signature against the peer's listed keys and holds `product.tenant_id` to the
**consumer's** tenant (`admission.py::_check_policy_bindings`). Eligibility is
`producer-attested`.

The identity model of §2 maps onto it without change: expected producer
identity = the trust-policy entry (governed state); tenant the child was
governed under = **not carried** — a peered product claims the *consumer's*
tenant, with governance context in the protected header; provider
relationship = `peered`. So the one concrete difference is **what
`contract.tenant_id` means on the wire**: for a peered product, *the tenant it
is admissible to*; for an `mcp-product` child, *the tenant that governed it*.
The two coexist because admission reads the field per acquisition kind and
never as one rule. This package **does not** change peering to carry a
producer-side tenant; it records the divergence as a question for a later
decision (§12, Q3) rather than a defect, because peering's trust model is
coherent on its own terms and nothing in CP-14 exercises it.

---

## 10 · Success criteria — the thirteen proofs, each with its instrument

Every proof is a test against real machinery: a producer in **another
process** (the `tests/crossproc` server pattern — a `build_egress_server` door
over a fixture product, loopback URL, bearer token from a file token source,
`SyncMcpBridge`), a consumer deployment booted from artifacts including one
`ccf.mcp-producer`, a granted `mcp_product` skill and a `GrantBoundChildResolver`
with `child_questions`.

| # | Proof | Instrument | Divergence under sabotage |
| --- | --- | --- | --- |
| 1 | Two argument sets to one producer return two corresponding governed products | two composite requests differing only in the mapped `subject`; assert the two admitted children's `DoorOutcome.request` echoes equal the two questions sent **and** their content addresses differ **and** each payload carries its own subject | make dispatch drop `parameters` → echoes equal each other → `question-mismatch` or identical addresses |
| 2 | Producer assembler absent from the consumer process | after a real acquisition, assert no module from the producer's package is in `sys.modules` of the consumer, and the consumer's `ArtifactStore` holds no producer replay record | import the producer's module in the door → RED |
| 3 | Expected producer identity is governed, not caller-authored | the invocation's `producer_id` equals the registration artifact's; constructing `McpProductInvocation` outside `dispatch_skill` and offering it is refused by `invocation_from_dispatch` (provenance) | bypass the registry copy → `ProvenanceForgeryError` absent → RED |
| 4 | Expected producer-side tenant is governed, not payload-authored | change **only** the child's `tenant_id` on the wire (a proxy door rewriting bytes) → `producer-tenant-mismatch`; change only the registration artifact → the expectation moves and the same bytes are refused the other way | remove check 1p → both admit → RED |
| 5 | Wrong producer identity refuses | proxy door rewrites `DoorOutcome.producer.producer_id` → `producer-mismatch` (tenant still equal) | remove 1q′ → admits → RED |
| 6 | Wrong producer-side tenant refuses | registration says `cp-05-demo`, producer governs under `cp-05-other` → `producer-tenant-mismatch` at 1p; and a `replay_ref` under another tenant → 1p′ | remove 1p′ alone → the replay-ref case admits → RED |
| 7 | Self-claimed identity cannot authorize | a door whose bytes claim the expected producer and tenant, reached through **no** registration (binding names an unregistered server) → `McpSkillUnregistered` before any socket; through a registration for a **different** producer → `producer-mismatch` | make the gate read `producer_id` from the door instead of the invocation → admits → RED |
| 8 | Correct class/version still required | producer serves `X@2.0.0` for a requirement `X` from `1.0.0` → `version-incompatible`; serves `Y` → `class-mismatch` (checks 2–3 unchanged) | skip checks 2–3 on the producer leg → RED |
| 9 | MCP eligibility records `provider-controls` | row `eligibility_basis == "provider-controls"`, `producing_fabric == producer_id` | claim `local-register` → RED |
| 10 | Consumer local-register silence cannot authorize | supersede an entity in the **consumer's** register that the child's payload names; the child still admits (the register is not consulted) **and** the row does not name `local-register`; the mirror: a `local-dispatch` child of the same shape refuses (`D-IMPL-334`) — the two legs diverge on the same data | consult the register on the producer leg → the first half flips → RED |
| 11 | Replay identifies the exact producer and admitted child | stop the producer process; `replay()` in a fresh environment reproduces the parent's content address and the row carries `producer_id`, `producer_tenant`, `producer_registration_address`, `child_content_address`, `child_question_address` | delete the retained admitted contract → replay refuses; restart the producer → replay must still not call it (one-shot counter) |
| 12 | No request argument becomes a network address | static: no code path from `ChildQuestion` to `McpResourceClient.url` or to a URI string (a lint over `child_resolver` / `dispatch` for `url`/`uri` construction from question fields); dynamic: a question with `subject="http://evil"` reaches the producer as a *subject string* — the producer's echo carries it, the consumer's client contacted only the registered URL (a recording `http_client_factory`) | interpolate the subject into the address → the recording factory sees a second host → RED |
| 13 | Existing local same-fabric behavior unchanged | the whole `tests/products` composite suite and `tests/crossproc/test_composite_provider_independence.py` pass byte-identically; `child_arguments` resolvers take the legacy call (a factory-call spy shows no `resolve_for`); `mcp` fixed-resource reads unchanged | any of them RED |

Failure roster discipline as for 338/339: compared to the baseline by exact
test identity, none new, none gone; the fragments-claim red, the lint-runner
reds and the other standing failures are neither absorbed nor repaired.

---

## 11 · Sabotage plan — every gate diverges, none by declaration

Each sabotage is a one-line edit to the **call site or the check**, never to
the verifier alone (the `D-IMPL-337` lesson: S7 reverted a call site and 24
controls stayed green). Restoration is verified **by marker**, never by a clean
`git status`.

| Id | Sabotage | Must go RED |
| --- | --- | --- |
| S1 | `_invoke_mcp_product` calls `read_text(uri)` on a fixed resource instead of the tool | proofs 1, 12 |
| S2 | copy `producer_id` / `producer_tenant` from the **door** instead of the registration | 3, 4, 7 |
| S3 | delete check 1p (tenant equality) | 4, 6 |
| S4 | delete 1p′ (replay-ref tenant) | 6 (second half) |
| S5 | delete 1q′ (assertion equality) | 5 |
| S6 | delete 1r (question echo) | 1 |
| S7 | producer leg consults `refuse_dependency_invalidation` | 10 |
| S8 | producer leg reports `local-register` | 9 |
| S9 | replay resolves the child through the registry instead of the retained bytes | 11 |
| S10 | `GovernedResolver` calls `resolve_for` unconditionally (no `isinstance`) | 13 (legacy resolvers raise) |
| S11 | `ProducerRegistration` constructed outside `register_producer` is accepted | 3 (guarded-provenance lint + control) |
| S12 | a literal URL in a `ccf.mcp-producer` artifact is accepted | No-Hardcoding lint control |
| S13 | `producer-unavailable` path re-raises instead of refusing | §8 case 2 proof |
| S14 | the door omits `producer` and the leg admits anyway | `producer-unasserted` proof |

Population checks the plan owes: every new refusal reason is emitted on
exactly one path (a census test over the source, on the `CP14-F-10`
precedent); every proof asserts on a **non-empty** population (the two-question
proof asserts two distinct addresses, never "no error").

---

## 12 · What still needed Dave before implementation — RULED (2026-09-14)

**Implementation GO.** Q1: `producer-unavailable` is a governed outcome that preserves the child-resolution evidence and follows the `D-IMPL-338` refusal-record discipline; an unregistered producer or a malformed artifact stays a deployment/configuration **error** — the two are never collapsed. Q2: ship `DoorOutcome.producer`, additive, sourced from the governed registration / verified door path. Q3: peering unchanged; the two `tenant_id` meanings are recorded as belonging to different provider relationships, no follow-up. Q4: one registration per producer with an `offers` list. Q5: `mcp_product` as its own skill type. Dave's full sixteen-item ruling is in `docs/DECISIONS.md` under *D-IMPL-340 — IMPLEMENTATION GO*; the proof package there is **fourteen** proofs (this package's thirteen plus *question echo/binding mismatch refuses*, which §6's 1r already carries).

*The questions as they were put, kept for the record:*


- **Q1 — `producer-unavailable` as a governed refusal (§8 case 2).** Today an
  MCP transport failure during composition is an exception. This package
  proposes a refusal with rows. Rule it, or keep the exception.
- **Q2 — the door assertion.** Ship `DoorOutcome.producer` (recommended: it
  is what makes proof 5 distinct from proof 6, and it is additive), or accept
  that producer identity for MCP is the registration alone and proofs 5/6
  collapse into one observable.
- **Q3 — peering's `tenant_id` semantics (§9).** Record the divergence and
  leave peering alone (recommended), or open a follow-up decision to carry a
  producer-side tenant in the protected header.
- **Q4 — registration granularity.** One `ccf.mcp-producer` per producer with
  an `offers` list (proposed), or one per (producer, class).
- **Q5 — the sixth skill type.** `mcp_product` as a new `SkillType` (proposed)
  versus a second binding shape under `mcp`.

Implementation phases, if approved: **(i)** artifact + registry + client
primitive + binding + dispatch, with the producer in another process and
proofs 1, 2, 12, 13; **(ii)** admission leg, refusal reasons, `ChildInvocation`
fields, proofs 3–10; **(iii)** replay fields and proof 11; then the sabotage
matrix, guarded-provenance registry rows, surface-change fragment, the close
panel, and `D-GATE-340`. Each phase's roster diffed against the baseline by
exact identity.

---

## 13 · The three prerequisites CP-14 still has, outside this package

Recorded here because they were measured in the same sitting and Dave ruled
each; none is `D-IMPL-340` work.

- **`CP14-F-22` — the spread producer does not serve on the current SDK.**
  Measured on `main c635037f`, cp-03's own `run.py` against the curated estate:
  refused at `ProductRequestContract.from_declared` — *"the request contract
  for 'credit-risk.spread' at class lane '1.0.0' declares 'intent' under
  arguments.properties, which is a shadow of the top-level request field
  ProductRequest.intent … (D-IMPL-264 D-01, amendment 1 F-2)"*. The strict
  xfail quarantine (13 of 17 tests) is **real, not stale**. The second
  quarantined defect (`build_replay_record` without `resolution`,
  `produce.py:408-423`) sits behind this one and could not be reached. Dave's
  options stand: repair rung 3 in its own phase, or supply another real
  governed producer of the exact required class. The `cp-04-canonical` rung
  is the precedent for a canonical sibling beside a frozen specimen.
- **`CP14-F-20` — RULED: the collateral slot is facility-grain.** The CP-14
  request names the `facility_id` explicitly beside the obligor; the mapping
  passes it to the collateral skill; no first/largest/fan-out/raw-store
  substitute. A consolidated multi-facility collateral context would be a
  different product class.
- **`CP14-F-21` — a separate behavioral finding, population measured:**
  16 of 19 shipped trees raise for an unresolvable anchor or source instead of
  returning a governed refusal (AST census over non-test modules; e.g.
  cp-04-canonical `acquisition.py:352` `LookupError`, cp-05 `assembler.py:111`
  and `produce.py:272`, cp-06 `acquisition.py:262`, cp-07, cp-08
  `UnknownFacility`, cp-09 `UnknownClient`, cp-11 `UnknownObligor`, cp-12
  `UnknownTrade`, cp-13 `UnknownCovenantSource` / `ValueError`). Twelve of the
  thirteen ladder rungs are in the population; only cp-10 is not. Whether it
  blocks a CP-14 required scenario depends on `CP14-F-24` (the CION scenario),
  which is still Dave's; from the consumer side §8 case 2 makes a raised
  producer a `producer-unavailable` refusal rather than a crash.
- **`CP14-F-19`** — estate limitation, kept visible; nothing tuned.

---

## 14 · As built (candidate `4c822611`) — departures from this package, stated

Everything in §2–§9 shipped as designed, with these differences a reviewer
should meet here rather than in the diff:

- **`ProducerRegistration` is a plain contract, not a minted type.** The
  registry builds it from the parsed `ccf.mcp-producer` document
  (`producer_registration_from_artifact`) and the composition root is the
  only caller — the same trust level as `McpSkillRegistry.register` today. The
  mint that matters is on the **dispatch value**: `McpProductInvocation` is a
  frozen dataclass with a module-private token, verified at
  `invocation_from_dispatch` (registered in `ccf.contracts.guarded`). §11's
  S11 therefore became *"verify the class, not the mint"* on the invocation.
- **The question-bound resolver is a second class.** `QuestionBoundChildResolver`
  implements `resolve_for` and no legacy call, so a `GovernedResolver` reaches
  it with the effective request or not at all; `GrantBoundChildResolver` is
  untouched. A composite that mixes a remote producer with a same-fabric child
  passes `child_arguments` as well; without one, a non-`mcp_product` grant is
  refused as `unsupported-outcome` rather than asked nothing.
- **The tenant asked is the registration's.** Over a real door, a registration
  expecting the wrong producer tenant is refused by the *producer* (the row is
  `ineligible` — *the child's own door refused*), because `tenant` on the tool
  call comes from `producer_tenant` and never from the mapping. The
  byte-identical `producer-tenant-mismatch` proof is the in-process one; both
  are in the package.
- **A refused door names its producer too.** An `ineligible` row from an
  `mcp_product` acquisition carries the producer members (ruling 9), which the
  package's §7 listed only for admitted and unavailable rows.
- **`producers:` derives; the composition root registers.** The config
  section derives one `ccf.mcp-producer` artifact per label into the manifest
  (the `policy_constraints` discipline); `load_config_and_boot` builds no MCP
  client and holds no bridge, so the composition root calls
  `ccf.skills.producers.register_declared_producer` over the parsed artifacts.
  Wiring that into boot would put a bridge lifetime and a credential factory
  inside the loader — a follow-up if a deployment asks for it, not a gap in the
  ruling.
- **`Agent.invoke_skill` refuses `mcp_product` by name** before dispatch; the
  design did not name the agent surface.
- **No lint scans YAML for literal URLs.** The `ccf.mcp-producer` validator
  refuses an address-shaped or token-shaped value at parse (a regex over the
  environment-variable name); `tools/lints/no_hardcoding.py` walks Python only
  and was not widened.
- **Schema drift that predates the branch was left as it was:**
  `ccf.half-life-table.json`, `ccf.eligibility-evidence-policy.json` and the
  missing `ccf.entity-invalidation-register.json` were regenerated by
  `make schemas` and restored, so the three standing `test_schema_export` reds
  stay exactly the reds they were.
