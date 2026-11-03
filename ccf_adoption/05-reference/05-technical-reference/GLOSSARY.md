# SDK Glossary

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`

## Context Product
Typed, governed, decision-ready unit of meaning carrying payload plus validity, lineage/evidence, policy/debt semantics and governed refusal behavior.

## ProductRequest
Typed question asked of a product: subject, instant, intent, freshness, parameters and overrides.

## ProductRequestContract
Governed accepted-question declaration. Current main can declare `subject_domain` and regex/domain constraints through `ArgumentDomain`.

## Governed refusal
A valid governed “no.” It is data, not a transport exception.

## TemporalBoundaryPolicy
Tenant-scoped declaration of permitted past age and clock skew for question/decision time. No SDK default is assumed.

## served_at
Trusted fabric serve instant used/retained by current temporal controls. Distinct from caller-supplied `asked_at`.

## TemporalWriteRefused
Named refusal when ingress evidence is outside the declared temporal bound.

## IdentityRefused
Named L2 refusal when a safe entity identity cannot be minted.

## Context Graph / GraphView
Governed L3 state and the admitted snapshot-scoped view.

## Projection — Π
Typed, perspective-conditioned transformation. Not presentation-time RBAC filtering.

## Context Half-life — λ_c
Calibrated decay of decision relevance. Not TTL.

## Context Debt — D_c
Quantified shortfall between context required and context assembled.

## Control Plane
Versioned governance/audit plane holding declarations and exact versions.

## ApprovalPolicy
Pinned HITL declaration of principals eligible to approve a gate.

## SignedHitlAction
Human-signed action claim bound to event/content/subject/time/nonce; replaces the earlier signed-principal-binding public API on current main.

## IssuanceClaims
Signed peering issuance metadata: issuance time, nonce and the question/request that was answered.

## SeenNonceSetProtocol
Deployment seam for peering replay detection. The reference in-process implementation is not a distributed nonce service.

## Authorized capability
Action-bound runtime authority for one tenant/principal/action/resource/decision.

## FileArtifactStore
File-backed content-addressed store. Current main requires declared `write_kinds` and refuses an unsafe root through `InsecureArtifactStoreRoot`.

## Decision Replay
Exact reconstruction of a served or refused determination against retained/pinned evidence.

## Paved road
Normal product-authoring path using `open_product` / `OpenedProduct`.

## Peering
Governed product exchange across fabrics/organizations, including trust, signature, issuance, contract, payload and lineage admission controls.

## MCP
Integration/transport protocol used at several CCF boundaries. MCP is not synonymous with Peering.

## HITL
Governed human action: approval, escalation, override and review.

## Assembly Mode
Product trust path: algorithmic, LLM-packaged or swarm-assembled.

## Gate 1 / Gate 2
Engineering review gates for product specification and post-build evidence closeout; distinct from runtime HITL.

## WriterLease

A held exclusion mechanism for a graph writer, declaring its scope and mechanism. Network stores refuse writer minting without a declared cross-process lease; process scope is not cross-process exclusion.

## ClassificationAuthority

Boot-minted authority from the pinned resolution specification, checked by classification readers and operators. A hand-declared object is not authority.

## Erasure consult

Artifact-store decoration that withholds whole-artifact reads against validated erasure evidence. It does not destroy retained bytes or erase graph claims.

## Product roster

Within-tenant product reach declared on a verified transport token grant. Omitted/null means tenant-wide; an empty set means no product. It does not replace product policy.

## Context Skill

**Context Skill:** descriptive term for a governed catalog entry plus grant permitting a composing agent to ask a Context Product. Not an SDK class and not an ordinary model tool. **Agent Skill:** external harness instruction/workflow; naming a Context Skill does not grant it. **Evidence root:** persistent directory supplied to `open_product` for retained replay evidence, separate from temporary scratch. See [Context Skills](CONTEXT_SKILLS.md) and [Decision Replay](DECISION_REPLAY.md).
