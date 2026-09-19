# D-IMPL-340 — parameterized cross-deployment child acquisition and admission

Applied 2026-09-14 under `D-IMPL-340`, the ruling recorded in `docs/DECISIONS.md`
(*IMPLEMENTATION GO*, sixteen items) and designed in `docs/D-IMPL-340-DESIGN.md`.
Baseline `main` @ `c635037f`; branch `d-impl-340-cross-deployment`.

## The gap

A composite could not acquire a child produced by another deployment. No skill
transport carried a question to a producer outside this fabric (`local_callable`
presumed this fabric's store and register; fixed-resource `mcp` read one
registered URI; `peering` drained a transport), the composite's request never
reached the child mapping, and `CompositeAdmissionGate` held every child to the
consumer's tenant — measured on the ruled pattern-to-copy as `tenant-mismatch`.

## What changes — direction B with the identity refinement

A sixth skill type, `mcp_product`, asks a **registered** remote producer a
governed question through the producer's existing `request_context_product`
tool. The producer is declared once, as a `ccf.mcp-producer` Control Plane
document (logical name, producer identity, producer tenant, an `offers` list,
and the **names** of the environment variables the endpoint and credential are
read from). That registration is the authority for the expected producer
identity and producer-side tenant; the answer — the child's `tenant_id`, its
replay reference, the door's new `ProducerAssertion`, its echo of the question —
is evidence held against it. Equality never authorizes; inequality refuses,
with wrong producer and wrong producer tenant as distinct reasons. Eligibility
stays `provider-controls`; the local register is neither consulted nor
credited; replay rows name the producer, its tenant, the registration's content
address and the question's address. A registered producer that cannot answer is
a governed `producer-unavailable` outcome; an unregistered one stays an error.
Local dispatch, fixed-resource `mcp` and peering are byte-identical.

## Surface entries

## ccf.skills.catalog.McpProductBinding

- Surface: ccf.skills.catalog.McpProductBinding
- Public surface: true
- Change type: added
- Before: no binding could name a producer to ask.
- After: `McpProductBinding(server, product_class, product_version)` — the descriptor of an `mcp_product` entry; `produces` must equal `product_class`.
- Why: ruling 5 — `mcp_product` is its own skill type, never a second reading of `mcp`.
- Migration: none; existing entries are unchanged.

## ccf.skills.dispatch.ProducerOffer

- Surface: ccf.skills.dispatch.ProducerOffer
- Public surface: true
- Change type: added
- Before: —
- After: one product class with a version floor a registered producer may be asked for; `accepts(version=)` is the same caret-shaped rule `ChildRequirement` uses.
- Why: ruling 4 — one registration per producer, with an offers list.
- Migration: none.

## ccf.skills.dispatch.ProducerRegistration

- Surface: ccf.skills.dispatch.ProducerRegistration
- Public surface: true
- Change type: added
- Before: —
- After: the registry's view of one `ccf.mcp-producer` document — `server`, `producer_id`, `producer_tenant`, `offers`, `artifact_address`; the authority admission holds an answer to.
- Why: ruling 4.
- Migration: none.

## ccf.skills.dispatch.ProductQuestion

- Surface: ccf.skills.dispatch.ProductQuestion
- Public surface: true
- Change type: added
- Before: —
- After: the governed question an `mcp_product` dispatch carries — subject, intent, freshness, aware `asked_at`, parameters, and the canonical `request_json`; `address` is its identity.
- Why: ruling 6 — the structured request carries the question; no argument becomes an address.
- Migration: none.

## ccf.skills.dispatch.McpProductInvocation

- Surface: ccf.skills.dispatch.McpProductInvocation
- Public surface: true
- Change type: added
- Before: —
- After: the minted result of one executed `mcp_product` dispatch; producer members copied from the resolved registration; verified by `verify_mcp_product_invocation` at the composite boundary (`D-IMPL-337`).
- Why: ruling 3/8 — expected identity and tenant come from governed state, never from the answer.
- Migration: none.

## ccf.skills.dispatch.McpProductFailure

- Surface: ccf.skills.dispatch.McpProductFailure
- Public surface: true
- Change type: added
- Before: —
- After: a registered, governed producer that could not answer (timeout, unreachable, tool error), returned as a value so admission can record a `producer-unavailable` row.
- Why: ruling 1 — never collapsed with a mis-wired deployment, which still raises.
- Migration: none.

## ccf.skills.dispatch.McpProductProvenanceError

- Surface: ccf.skills.dispatch.McpProductProvenanceError
- Public surface: true
- Change type: added
- Before: —
- After: raised when an `McpProductInvocation` reaches a boundary without the dispatch mint.
- Why: `D-IMPL-337`.
- Migration: none.

## ccf.skills.dispatch.ProducerDoesNotOffer

- Surface: ccf.skills.dispatch.ProducerDoesNotOffer
- Public surface: true
- Change type: added
- Before: —
- After: an `McpSkillUnregistered` subclass — the producer is registered but does not offer the binding's class or lane; refused before any socket is opened.
- Why: ruling 1 — a deployment fact is an error, not a governed child refusal.
- Migration: none.

## ccf.skills.dispatch.verify_mcp_product_invocation

- Surface: ccf.skills.dispatch.verify_mcp_product_invocation
- Public surface: true
- Change type: added
- Before: —
- After: refuses anything that is not a minted `McpProductInvocation`; the boundary check `invocation_from_dispatch` runs.
- Why: `D-IMPL-337` — the sentinel is verified, not the class.
- Migration: none.

## ccf.skills.dispatch.dispatch_skill

- Surface: ccf.skills.dispatch.dispatch_skill
- Public surface: true
- Change type: reshaped
- Before: `dispatch_skill(entry, *, arguments, callable_registry, mcp_skills=None, peering_skills=None)` returning `SkillInvocation | ToolInvocation | McpInvocation | PeeringInvocation`.
- After: gains `question: ProductQuestion | None = None` (required for an `mcp_product` entry, ignored by every other) and may return `McpProductInvocation | McpProductFailure`; every existing branch is byte-identical.
- Why: ruling 6 — the question is structured, never a string mapping.
- Migration: none for existing callers; a caller that switches on the result type gains two shapes.

## ccf.skills.dispatch.McpSkillRegistry

- Surface: ccf.skills.dispatch.McpSkillRegistry
- Public surface: true
- Change type: behavior
- Before: `register(server, client, resources)` / `resolve(binding)`.
- After: adds `register_producer(*, client, registration)` and `resolve_producer(binding)`; the fixed-resource pair is unchanged and a logical name cannot be registered as both.
- Why: ruling 10 — logical registration names, never caller URLs. The manifest records a class's constructor shape, not its methods, so this change has no diff line; the entry's type was corrected from `reshaped` to `behavior` at the `f0656746` qualification (2026-09-19).
- Migration: none.

## ccf.skills.producers.register_declared_producer

- Surface: ccf.skills.producers.register_declared_producer
- Public surface: true
- Change type: added
- Before: —
- After: names → client → registration: reads the two named environment variables, builds the shared MCP client on the deployment's bridge and credential factory, registers the producer. The only place a producer's URL or credential is resolved.
- Why: CINV-01 — deployment values at the composition root.
- Migration: none.

## ccf.skills.producers.producer_registration_from_artifact

- Surface: ccf.skills.producers.producer_registration_from_artifact
- Public surface: true
- Change type: added
- Before: —
- After: the registry's `ProducerRegistration` for one parsed `ccf.mcp-producer` document, carrying the document's content address.
- Why: replay names the governance context of every acquisition.
- Migration: none.

## ccf.skills.producers.ProducerEnvironmentMissing

- Surface: ccf.skills.producers.ProducerEnvironmentMissing
- Public surface: true
- Change type: added
- Before: —
- After: a named environment variable is not set — a configuration error, raised.
- Why: ruling 1.
- Migration: none.

## ccf.mcp.client.McpResourceClient

- Surface: ccf.mcp.client.McpResourceClient
- Public surface: true
- Change type: reshaped
- Before: `read_text`, `resource_uris`, `resource_templates` and their async forms.
- After: adds `call_tool_text(name, arguments)` / `call_tool_text_async` — one tool call on the same session-per-call lifetime, bridge deadline and `http_client_factory`; the URL is the client's, fixed at construction.
- Why: capability A — ask through the producer's existing tool.
- Migration: none.

## ccf.mcp.errors.McpToolFailed

- Surface: ccf.mcp.errors.McpToolFailed
- Public surface: true
- Change type: added
- Before: —
- After: the server ran a tool and reported `isError`; carries the reported text verbatim as `text`.
- Why: a completed-but-failed call is distinct from an unreachable server.
- Migration: none.

## ccf.products.producer.ProducerAssertion

- Surface: ccf.products.producer.ProducerAssertion
- Public surface: true
- Change type: added
- Before: —
- After: `(producer_id, tenant_id)` a door stamps on its answers; re-exported by `ccf.products.door`. A claim, never an authority.
- Why: ruling 2 — wrong producer and wrong producer tenant stay independently testable.
- Migration: none.

## ccf.products.door.DoorOutcome

- Surface: ccf.products.door.DoorOutcome
- Public surface: true
- Change type: reshaped
- Before: `request, product_json, content_address, replay_ref, refusal`.
- After: adds `producer: ProducerAssertion | None = None`, hash-transparent at `None`, stamped on both branches.
- Why: ruling 2.
- Migration: none; every pre-340 door's bytes are unchanged.

## ccf.products.door.door_answer

- Surface: ccf.products.door.door_answer
- Public surface: true
- Change type: reshaped
- Before: `door_answer(resolved, *, echo, resolved_request)`.
- After: adds `producer: ProducerAssertion | None = None`.
- Why: ruling 2.
- Migration: none.

## ccf_runtime.mcp.egress.build_egress_server

- Surface: ccf_runtime.mcp.egress.build_egress_server
- Public surface: true
- Change type: reshaped
- Before: no producer identity.
- After: `producer_id` and `producer_tenant`, supplied together or not at all; when supplied every outcome the door emits carries the assertion.
- Why: ruling 2 — the assertion originates from the governed door path.
- Migration: none.

## ccf.controlplane.artifacts.McpProducerRegistration

- Surface: ccf.controlplane.artifacts.McpProducerRegistration
- Public surface: true
- Change type: added
- Before: —
- After: the `ccf.mcp-producer` Control Plane artifact class (`MCP_PRODUCER`): `server`, `producer_id`, `producer_tenant`, `endpoint_from_env`, `credential_from_env`, `offers`; a literal URL, host, port or token is refused at parse.
- Why: ruling 4 and 10.
- Migration: none.

## ccf.controlplane.artifacts.DeploymentConfig

- Surface: ccf.controlplane.artifacts.DeploymentConfig
- Public surface: true
- Change type: reshaped
- Before: no producer section.
- After: an optional `producers:` mapping, one `ccf.mcp-producer` body per label, derived per key on the `policy_constraints` discipline.
- Why: ruling 4.
- Migration: none; a config without the section derives exactly what it did.

## ccf.products.composite.RequestAwareChildResolverProtocol

- Surface: ccf.products.composite.RequestAwareChildResolverProtocol
- Public surface: true
- Change type: added
- Before: child resolvers received `requirements, asked_at, admitted_at, composition_invocation, consumer_lineage`.
- After: a capability Protocol whose `resolve_for(...)` also receives the composite's **effective** request; `GovernedResolver` calls it on a resolver that declares it and the legacy call otherwise. `CompositeChildResolverProtocol` is not widened.
- Why: ruling 6 — `ChildQuestions` derives from the effective request; no defaulted Protocol keyword.
- Migration: none.

## ccf.products.composite.CompositeAdmissionGate

- Surface: ccf.products.composite.CompositeAdmissionGate
- Public surface: true
- Change type: reshaped
- Before: check 1 held every child to the consumer's tenant.
- After: for the `mcp-product` acquisition kind a producer leg replaces check 1 — child tenant and replay-reference tenant to the registration's producer tenant, the door's assertion to the registration's producer identity and tenant, the echo to the question sent — then checks 2–7 unchanged; eligibility `provider-controls`. Every other kind is byte-identical.
- Why: ruling 8.
- Migration: none.

## ccf.products.composite.ChildRefusalReason

- Surface: ccf.products.composite.ChildRefusalReason
- Public surface: true
- Change type: reshaped
- Before: twenty reasons.
- After: adds `producer-tenant-mismatch`, `producer-mismatch`, `producer-unasserted`, `question-mismatch`, `producer-unavailable`; `ChildAcquisition` adds `mcp-product`.
- Why: ruling 8 and 1.
- Migration: none.

## ccf.products.composite.ChildAdmissionRefusal

- Surface: ccf.products.composite.ChildAdmissionRefusal
- Public surface: true
- Change type: reshaped
- Before: `product_class, reason, reported_content_address, verified_content_address`.
- After: adds `producer_id, producer_tenant, producer_registration_address, producer_server, question_address`, hash-transparent at `None`; a child refusal envelope now carries them (`null` on other legs).
- Why: ruling 9 — a refused `mcp_product` row still names its producer.
- Migration: none.

## ccf.products.child_resolver.QuestionBoundChildResolver

- Surface: ccf.products.child_resolver.QuestionBoundChildResolver
- Public surface: true
- Change type: added
- Before: only `GrantBoundChildResolver`, whose mapping never saw the composite's request.
- After: a resolver implementing `resolve_for`; `child_questions: ChildQuestions` maps a requirement and the effective request to a `ChildQuestion`; optional `child_arguments` for non-product entries granted to the same agent.
- Why: ruling 6.
- Migration: none; `GrantBoundChildResolver` is unchanged.

## ccf.products.child_resolver.ChildQuestion

- Surface: ccf.products.child_resolver.ChildQuestion
- Public surface: true
- Change type: added
- Before: —
- After: `subject, intent, freshness, parameters` — the four members the producer takes from the question; no path to an address.
- Why: ruling 6.
- Migration: none.

## ccf.replay.record.ChildResolution

- Surface: ccf.replay.record.ChildResolution
- Public surface: true
- Change type: reshaped
- Before: no producer relationship on a row.
- After: adds `producer_id, producer_tenant, producer_registration_address, producer_server, child_question_address, child_replay_ref`, hash-transparent at `None`; `CHILD_OUTCOME_STATUSES` adds `producer-unavailable`.
- Why: ruling 9.
- Migration: none; every existing row hashes as it did.

## ccf.agents.agent.Agent

- Surface: ccf.agents.agent.Agent
- Public surface: true
- Change type: behavior
- Before: `invoke_skill` dispatched any bound entry.
- After: refuses an `mcp_product` entry by name — a producer is asked by a composite through a `ProductQuestion`, not by an agent's string-argument invocation.
- Why: ruling 6. The manifest records a class's constructor shape, not its methods, so this change has no diff line; the entry's type was corrected from `reshaped` to `behavior` at the `f0656746` qualification (2026-09-19).
- Migration: none.

## Claimed at the `f0656746` qualification

The eight entries below were added by `D-IMPL-340`'s two commits — `4c822611` (the feature) and
`dcfb8608` (the review-closing fix) — and were left unclaimed when this fragment was written.
Recorded 2026-09-19 from those commits; nothing about the names changed.

## ccf.controlplane.artifacts.MCP_PRODUCER

- Surface: ccf.controlplane.artifacts.MCP_PRODUCER
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactClass(class_id="ccf.mcp-producer", contract=McpProducerRegistration)` — the class id a deployment registers a producer under; deployment binding only, naming a producer and what it may be asked for, holding no address and no secret
- Why: `D-IMPL-340` (`4c822611`) — the producer registration is a Control Plane artifact and needs a class id a manifest can address
- Migration: none

## ccf.controlplane.artifacts.ProducerOfferDeclaration

- Surface: ccf.controlplane.artifacts.ProducerOfferDeclaration
- Public surface: true
- Change type: added
- Before: absent
- After: a `CCFContract` — `product_class`, `versions_from` (a semver floor, validated) — one product class a registered producer may be asked for
- Why: `D-IMPL-340` (`4c822611`) — a producer offers named classes from a version floor, never everything it holds
- Migration: none

## ccf.products.child_resolver.ChildQuestions

- Surface: ccf.products.child_resolver.ChildQuestions
- Public surface: true
- Change type: added
- Before: absent
- After: the type alias `Callable[[ChildRequirement, ProductRequest], ChildQuestion]` — the question factory a question-bound child resolver is built from
- Why: `D-IMPL-340` (`4c822611`) — a producer is asked a `ProductQuestion` built from the requirement and the parent's request, and the factory that builds it is a declared seam
- Migration: none

## ccf.products.child_resolver.MalformedDoorAnswer

- Surface: ccf.products.child_resolver.MalformedDoorAnswer
- Public surface: true
- Change type: added
- Before: absent
- After: a `ValueError` raised for a completed producer call whose text is not a `DoorOutcome`; the producer leg decodes the door's answer in full — its producer assertion, its echo of the question, the axes it answered and its replay reference — or raises this
- Why: `D-IMPL-340` (`dcfb8608`) — a refused or malformed door is held by name rather than read as an empty answer
- Migration: none

## ccf.products.door.AnsweredQuestion

- Surface: ccf.products.door.AnsweredQuestion
- Public surface: true
- Change type: added
- Before: absent — `DoorOutcome.request` echoed the wire request and nothing else; `subject`, `intent` and `freshness` reached a door as separate arguments and came back on no channel at all
- After: a `CCFContract` — `subject`, `intent`, `freshness`, `asked_at` — the four §6.3 axes a door actually answered, stated from the typed request it resolved and never from the caller's text; the composite's question-identity check recomputes over all of them
- Why: `D-IMPL-340` (`dcfb8608`) — a consumer holding an answer to the question it asked needs every axis echoed
- Migration: none

## ccf.products.door.ProducerAssertion

- Surface: ccf.products.door.ProducerAssertion
- Public surface: true
- Change type: added
- Before: absent
- After: a re-export of `ccf.products.producer.ProducerAssertion` (claimed above) from `ccf.products.door`, where `DoorOutcome.producer` carries it
- Why: `D-IMPL-340` (`4c822611`) — the door's outcome names the type it carries from the module a reader of the outcome already imports
- Migration: none

## ccf.skills.dispatch.question_identity

- Surface: ccf.skills.dispatch.question_identity
- Public surface: true
- Change type: added
- Before: absent
- After: `question_identity(*, request_json: str, subject: str, intent: str, freshness: str, asked_at: datetime) -> str` — `sha256` over the whole question, canonically; one function for both sides of the seam. `D-IMPL-342` (`342-01`) later changed the identity's bytes, and that `behavior` entry stands beside this one
- Why: `D-IMPL-340` (`dcfb8608`) — question identity over every axis, so a door's answer is held to the question the composite asked
- Migration: none

## ccf.skills.dispatch.verify_mcp_product_failure

- Surface: ccf.skills.dispatch.verify_mcp_product_failure
- Public surface: true
- Change type: added
- Before: absent
- After: `verify_mcp_product_failure(value: object) -> McpProductFailure` — refuses, with `McpProductProvenanceError` (claimed above), anything that is not an `McpProductFailure` minted by the dispatch, and returns the value narrowed
- Why: `D-IMPL-340` (`dcfb8608`), on `D-IMPL-337`'s pattern — provenance from the guarded construction path, not nominal type identity
- Migration: none
