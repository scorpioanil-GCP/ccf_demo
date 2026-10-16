# 385-01 (D-IMPL-385, 2026-10-16) — dimension 4 names the composing agent and its skill-set

`D-IMPL-385`, gap 2 of the skills feasibility probe. Dave, 2026-10-16 15:25 MST,
option C: *"Fix gap 2 now (the decision record never records which agent decided
or which skills it held)."*

Before this, a paved composite whose agent held grants in force recorded
`agent_definition_hash = "no-agent"` and `grant_set_hash = "no-grants"` in replay
dimension 4: `build_replay_record` had the agent seam (`agent_conditioning`), and no
caller in `src/` or `runtime/` passed it.

## ccf.products.composite.AgentConditionedChildResolverProtocol

- Surface: ccf.products.composite.AgentConditionedChildResolverProtocol
- Public surface: true
- Change type: added
- Before: no way for a child resolver to say which agent composed a decision.
- After: a runtime-checkable capability Protocol, `agent_conditioning(*, perspective) -> PerspectiveConditioning | None`. `GovernedResolver` asks a child resolver that declares it when it writes a decision's record (served or refused) and threads the answer into dimension 4; `None`, or a resolver that does not declare it, keeps the no-agent claims.
- Why: CLAUDE.md §6.2 — which agent and which skill-set made a decision must be answerable from replay alone. Red test: `tests/products/test_dimension_four_records_the_agent.py` (`'no-agent' == <agent hash>` on `5a3e9b9f`).
- Migration: none.

## ccf.products.child_resolver.GrantBoundChildResolver

- Surface: ccf.products.child_resolver.GrantBoundChildResolver
- Public surface: true
- Change type: reshaped
- Before: built from `agent_definition_hash` alone.
- After: optional `agent: AgentDefinition | None = None`, refused at construction unless its content hash equals `agent_definition_hash`; `agent_conditioning(perspective=...)` returns the caller's principal and role, the agent's hash, versioned URI and archetypes, and the ledger's grant-set hash for that agent read at the call. `QuestionBoundChildResolver` takes the same keyword and delegates.
- Why: `D-IMPL-385`.
- Migration: none; without `agent` the resolver records exactly as before.

## ccf.products.resolver.RefusalRecorderProtocol

- Surface: ccf.products.resolver.RefusalRecorderProtocol
- Public surface: true
- Change type: reshaped
- Before: `record(...)` took no agent conditioning.
- After: optional `agent_conditioning: PerspectiveConditioning | None = None`, recorded into dimension 4 (`ReplayRefusalRecorder` passes it to `build_replay_record`). The resolver passes it only for a decision an agent composed, and refuses at construction a recorder that cannot accept it when its child resolver declares `AgentConditionedChildResolverProtocol` (`refuse_incompatible_refusal_recorder(..., keyword="agent_conditioning")`).
- Why: `D-IMPL-385`.
- Migration: a deployment's own recorder composed over an agent-conditioned child resolver adds the keyword or takes `**kwargs`.

## ccf.products.child_resolver.QuestionBoundChildResolver

- Surface: ccf.products.child_resolver.QuestionBoundChildResolver
- Public surface: true
- Change type: reshaped
- Before: built from `agent_definition_hash` alone.
- After: optional `agent: AgentDefinition | None = None`, handed to the `GrantBoundChildResolver` it wraps; `agent_conditioning(perspective=...)` delegates to it. `open_product` passes the declared agent, so every paved composite's records name it.
- Why: `D-IMPL-385`.
- Migration: none.

## ccf.products.resolver.refuse_incompatible_refusal_recorder

- Surface: ccf.products.resolver.refuse_incompatible_refusal_recorder
- Public surface: true
- Change type: reshaped
- Before: checked only that `record` accepts `subject_withholding=`.
- After: optional `keyword: str = "subject_withholding"`; `GovernedResolver` also checks `agent_conditioning` when its child resolver declares `AgentConditionedChildResolverProtocol`.
- Why: `D-IMPL-385`.
- Migration: none; the default is the previous check.
