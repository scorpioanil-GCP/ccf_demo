# 343-01 — the paved road: one facade over the governed resolver, and the standard door

Applied 2026-09-15 under `D-IMPL-343` (Dave's IMPLEMENTATION GO, five rulings R-2/R-4/R-6/
R-7/R-13 and the locks recorded verbatim in `docs/DECISIONS.md`; design in
`docs/D-IMPL-343-DESIGN.md`). The measurement that opened it: the canonical spread producer
carried roughly as much SDK plumbing as domain logic, one copy of that plumbing had already
drifted from the contract (`CP03C-F-07`), and no example tree contained consumer wiring at
all. *"One facade over D-IMPL-336–340 — not three helpers."*

## What did NOT change, stated first

- **No existing call site breaks.** Every builder change is a relaxation or an added
  optional keyword; `GovernedResolver` gains one required field that every direct
  construction in the tree states (`acquisition=None` — the posture every earlier
  deployment had). The five frozen specimens and every canonical tree except the dogfood
  keep their doors and their builder calls unchanged.
- **No content address moves.** The three new `DeploymentConfig` sections and the new
  declaration field are hash-transparent at their sentinel; the dogfood tree's
  demonstration spread hashes to the same address and the same replay record before and
  after (`122e0a7b…` / `b3d1c7b1…`).
- **No second architecture.** There is no second resolver, registry, recorder or replay
  store; `OpenedProduct.build_arguments` returns the exact mapping the facade hands the
  builder, so the low road is reachable from the paved surface.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: added
- Before: absent — a producer wrote boot, effective-request re-derivation, ingest, a fifteen-keyword builder call, a store and a readback by hand
- After: one call binding `acquire`, `project`, `assess` and a gate to the two documents; refuses at open, by name
- Why: D-IMPL-343 — the plumbing burden is launch-blocking ergonomics, and the same plumbing had drifted in a copy
- Migration: none; `build_governed_resolver` stays the low road

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: added
- Before: absent
- After: `question`, `answer`, `record_of`, `resolve` (the door's `ProductResolverProtocol`), `build_arguments` (the low road), one registry, one store, one recorder
- Why: the object a door holds and a spine asks
- Migration: none

## ccf.products.product.AcquireProtocol

- Surface: ccf.products.product.AcquireProtocol
- Public surface: true
- Change type: added
- Before: absent — each tree wrote its own acquire-at-effective-parameters against a re-derived request
- After: `(AcquisitionContext) -> Iterable[SignalEnvelope]`, handed the EFFECTIVE request by the resolver's seam
- Why: R-4 — one derivation
- Migration: none

## ccf.products.product.AcquisitionContext

- Surface: ccf.products.product.AcquisitionContext
- Public surface: true
- Change type: added
- Before: absent
- After: the effective request, the perspective, the tenant, the resolved source settings and the instant
- Why: what `acquire` legitimately needs, and nothing it must re-derive
- Migration: none

## ccf.products.product.AssessProtocol

- Surface: ccf.products.product.AssessProtocol
- Public surface: true
- Change type: added
- Before: absent — each tree closed a scorer over `asked_at` and the booted artifacts
- After: `(AssessmentContext) -> DebtAssessment`
- Why: the developer owns the rule; the SDK hands the instant and the bindings
- Migration: none

## ccf.products.product.AssessmentContext

- Surface: ccf.products.product.AssessmentContext
- Public surface: true
- Change type: added
- Before: absent
- After: the view, the evidence, the DECISION instant, the booted λ_c table and profile, the admitted children
- Why: R-3c — the decision instant reaches the scorer from the resolver, never from a closure
- Migration: none

## ccf.products.resolver.AcquisitionSeamProtocol

- Surface: ccf.products.resolver.AcquisitionSeamProtocol
- Public surface: true
- Change type: added
- Before: absent — seven trees re-ran `ReferencePolicyConstraintResolver` to guess the effective request before booting
- After: the declared acquisition boundary, invoked once by `GovernedResolver.__call__` after resolution and before the graph read
- Why: R-4, verbatim: "Effective-request derivation runs once, on the governed call, and acquisition consumes that outcome"
- Migration: none; a deployment whose fabric is populated before the resolver passes nothing

## ccf.products.resolver.InstantAwareDebtScorerProtocol

- Surface: ccf.products.resolver.InstantAwareDebtScorerProtocol
- Public surface: true
- Change type: added
- Before: absent
- After: `score_at(view, evidence, decided_at, children)`, checked structurally FIRST by the resolver
- Why: R-3c; the D-IMPL-339 companion-Protocol precedent
- Migration: none; scorers implementing only `__call__` are asked as before

## ccf.products.resolver.declared_refusal_recorder

- Surface: ccf.products.resolver.declared_refusal_recorder
- Public surface: true
- Change type: added
- Before: absent — a door could not reach the per-question resolver's recorder and built a second one over a second store
- After: ONE `ReplayRefusalRecorder` built once from the declared binding and the bundle's content address, shared by the resolver and the door
- Why: served and refused decisions land in one store under one class
- Migration: none

## ccf.products.resolver.build_governed_resolver

- Surface: ccf.products.resolver.build_governed_resolver
- Public surface: true
- Change type: reshaped
- Before: `max_ttl_seconds` and `product_ttl_seconds` required ints; no recorder or seam keyword; `decision_instant_parameter` unchecked
- After: both TTL figures optional and read from the declared `ttl:` binding when omitted, held EQUAL when both speak (R-3a); `decision_instant_parameter` held equal to the class declaration (R-3b); `refusal_recorder=` and `acquisition=` accepted
- Why: D-IMPL-292 — no argument for a declared value
- Migration: none for existing calls; a call restating a declared TTL with a different value is now refused with both named

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: reshaped
- Before: no acquisition field; the scorer asked at most through the child-aware seam; `decided_at` bound after scoring
- After: a required `acquisition` field (`None` = no seam); the instant-aware scorer asked first; `decided_at` bound before scoring
- Why: R-4 and R-3c
- Migration: direct constructions state `acquisition=None`

## ccf.signal.envelope.refuse_foreign_envelope

- Surface: ccf.signal.envelope.refuse_foreign_envelope
- Public surface: true
- Change type: added
- Before: absent — nothing stated that `observed_at` is the ingestion instant (CP03C-F-08)
- After: an envelope naming another tenant or another instant is refused by name at the paved road's boundary
- Why: the ingest loop's tenant/instant bounds are the SDK's (Dave's lock)
- Migration: none

## ccf.deployment.keys.DeploymentKeys

- Surface: ccf.deployment.keys.DeploymentKeys
- Public surface: true
- Change type: added
- Before: absent — every canonical tree restated its section keys as string properties
- After: the derived keys by section, on `BootedFabric.keys`
- Why: keys are read, never restated
- Migration: none; `BootedFabric.keys` is `None` on the manifest form

## ccf.deployment.environment.EnvironmentDocument

- Surface: ccf.deployment.environment.EnvironmentDocument
- Public surface: true
- Change type: added
- Before: absent — each tree invented its own `backends.yaml` / `door.yaml` / `ttl.yaml` and its own reader
- After: the one environment document: substrate, source variable NAMES with remedies, door names, remote settings; a Control Plane value is refused by name
- Why: Dave's lock — no URLs or tokens in configuration; one shape, one reader
- Migration: none for existing trees; a paved tree writes `ccf_environment.yaml`

## ccf.deployment.environment.EnvironmentValue

- Surface: ccf.deployment.environment.EnvironmentValue
- Public surface: true
- Change type: added
- Before: absent
- After: `{from_env, remedy}` — a NAME and the deployment's own remedy text
- Why: names, never values
- Migration: none

## ccf.deployment.environment.SubstrateSettings

- Surface: ccf.deployment.environment.SubstrateSettings
- Public surface: true
- Change type: added
- Before: absent — `per_run: path` was declared and read by nothing
- After: the connection setting, prefix and suffix the facade mints a per-question path from; `src/` names no backend
- Why: CP03C-F-02's mechanism is the SDK's
- Migration: none

## ccf.deployment.environment.DoorEnvironment

- Surface: ccf.deployment.environment.DoorEnvironment
- Public surface: true
- Change type: added
- Before: absent
- After: the credential, issuer and resource-server NAMES the standard door reads
- Why: no URL or token in configuration
- Migration: none

## ccf.deployment.environment.RemoteSettings

- Surface: ccf.deployment.environment.RemoteSettings
- Public surface: true
- Change type: added
- Before: absent
- After: a consumer's one MCP deadline
- Why: the consumer half's environment block, declared now so the document's shape is complete
- Migration: none

## ccf.deployment.environment.EnvironmentMissing

- Surface: ccf.deployment.environment.EnvironmentMissing
- Public surface: true
- Change type: added
- Before: absent
- After: raised, with the document's remedy, when a named variable is unset
- Why: a configuration fact is an exception, never a governed refusal
- Migration: none

## ccf.deployment.environment.ENVIRONMENT_DOCUMENT_NAME

- Surface: ccf.deployment.environment.ENVIRONMENT_DOCUMENT_NAME
- Public surface: true
- Change type: added
- Before: absent
- After: `ccf_environment.yaml`
- Why: one name a reader knows to look for
- Migration: none

## ccf.deployment.environment.load_environment_document

- Surface: ccf.deployment.environment.load_environment_document
- Public surface: true
- Change type: added
- Before: absent
- After: reads and validates the document under a config root
- Why: one reader
- Migration: none

## ccf.deployment.environment.resolve_value

- Surface: ccf.deployment.environment.resolve_value
- Public surface: true
- Change type: added
- Before: absent
- After: one name → its value, or the remedy
- Why: one reader
- Migration: none

## ccf.deployment.environment.resolve_values

- Surface: ccf.deployment.environment.resolve_values
- Public surface: true
- Change type: added
- Before: absent
- After: every source setting resolved at once, every missing remedy carried together
- Why: an operator fixes the environment in one pass
- Migration: none

## ccf.controlplane.artifacts.TtlBinding

- Surface: ccf.controlplane.artifacts.TtlBinding
- Public surface: true
- Change type: added
- Before: absent — the two TTL figures lived in a side document and two builder keywords
- After: the `ttl:` section's class: `max_ttl_seconds`, `product_ttl_seconds`, declared once
- Why: R-3a
- Migration: none

## ccf.controlplane.artifacts.TTL_BINDING

- Surface: ccf.controlplane.artifacts.TTL_BINDING
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.ttl-binding` artifact class, typed-registerable
- Why: the reserved section derives it
- Migration: none

## ccf.controlplane.artifacts.EgressDoorBinding

- Surface: ccf.controlplane.artifacts.EgressDoorBinding
- Public surface: true
- Change type: added
- Before: absent — each door read its own document with its own required-key tuple; two carried a principal/role nothing compared
- After: the `door:` section's class: `producer_id`, `producer_tenant` (held equal to `tenant_id`, R-6), `tool_description`, `required_scope`; a principal, role, URL or credential is refused by name
- Why: one authority per value
- Migration: none

## ccf.controlplane.artifacts.EGRESS_DOOR

- Surface: ccf.controlplane.artifacts.EGRESS_DOOR
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.egress-door` artifact class, typed-registerable
- Why: the reserved section derives it
- Migration: none

## ccf.controlplane.artifacts.DeploymentConfig

- Surface: ccf.controlplane.artifacts.DeploymentConfig
- Public surface: true
- Change type: reshaped
- Before: no `ttl`, `door` or `agent` section
- After: the three sections, hash-transparent at `None`; `agent:` derives on the versioned path (R-2) and stays out of the typed table
- Why: D-IMPL-343 §5.1
- Migration: none; a config naming none of them derives byte-for-byte what it did

## ccf.controlplane.artifacts.ProductClassDeclaration

- Surface: ccf.controlplane.artifacts.ProductClassDeclaration
- Public surface: true
- Change type: reshaped
- Before: no `decision_instant_parameter`
- After: the field, hash-transparent at `None`, held equal to the builder keyword
- Why: R-3b; closes the 24.10-F-09 architecture question
- Migration: none

## ccf.deployment.BootedFabric

- Surface: ccf.deployment.BootedFabric
- Public surface: true
- Change type: reshaped
- Before: five fields
- After: a sixth, `keys`, defaulted `None`
- Why: the derived keys travel with the fabric
- Migration: none

## ccf.mcp.client.bearer_client_factory

- Surface: ccf.mcp.client.bearer_client_factory
- Public surface: true
- Change type: added
- Before: absent — each consumer wrote the same nineteen-line httpx factory
- After: a credential-carrying `HttpClientFactory` for `register_declared_producer`
- Why: the consumer half's one credential seam
- Migration: none

## ccf_runtime.mcp.auth.StaticTokenSource

- Surface: ccf_runtime.mcp.auth.StaticTokenSource
- Public surface: true
- Change type: added
- Before: absent — each door wrote a one-entry token file into a temporary directory
- After: recognised tokens held in memory, constant-time comparison
- Why: the standard door's per-boot credential
- Migration: none

## ccf_runtime.mcp.product_door.open_door

- Surface: ccf_runtime.mcp.product_door.open_door
- Public surface: true
- Change type: added
- Before: absent — six example doors carried the same ~106-line body
- After: the standard door over any `ServesProducts`: the entitlement policy into the ONE registry, the static token source, the declared-role perspective, the product's own recorder; three typed overrides
- Why: D-IMPL-343 §5.4
- Migration: none; `build_egress_server` stays the low road

## ccf_runtime.mcp.product_door.ProductDoor

- Surface: ccf_runtime.mcp.product_door.ProductDoor
- Public surface: true
- Change type: added
- Before: absent
- After: `server(issuer_url, resource_server_url)`, `serve_stdio()`, `serve_loopback(announce)`
- Why: the two transports, once
- Migration: none

## ccf_runtime.mcp.product_door.ServesProducts

- Surface: ccf_runtime.mcp.product_door.ServesProducts
- Public surface: true
- Change type: added
- Before: absent
- After: the structural Protocol a door serves — nine members a hand-composed deployment already holds
- Why: the paved road is not the only road
- Migration: none

## Regression evidence

`tests/products/test_paved_road.py` (the facade and the door through the public surface,
with the design's §12 sabotages that need no estate), `tests/deployment/test_paved_sections.py`
(the three sections, the keys, the environment document),
`tests/invariants/test_paved_road_writer_reach.py` (single-writer at the facade),
`tests/examples/test_spine_separation.py` (the `paved` shape, its floor, the `double-spined`
refusal), and the first executable proof — `examples/cp-03-canonical-obligor-financial-spread`
re-expressed in place with OFC-G01..G27 green by the same node ids against the live estate
and the cross-deployment proof green through `open_door`.

Standing and NOT this change's: `tests/deployment/test_class_lookup.py::
test_the_phases_fragments_claim_exactly_what_was_added` was red at the base commit with
names from D-IMPL-336..340 unclaimed by any fragment; this fragment claims only what
D-IMPL-343 added.
