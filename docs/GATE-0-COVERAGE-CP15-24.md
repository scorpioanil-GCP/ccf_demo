# Gate-0 coverage matrix — CP-15 through CP-24

**Status.** Revision 2, 2026-09-20, incorporating Dave's Gate-0 direction (five rulings, recorded
in `docs/DECISIONS.md` under *GATE-0 DIRECTION*). Returned for final approval. Revision 1 (commit
`96dcadde`) is the pass as run; this revision re-scopes CP-22, defines CP-23 and CP-24, adds the
developer-experience rubric adopters are to be measured against, re-evaluates the shared batches
under it, and gives the revised build sequence. No code, no CP-15–24 implementation, no decision id
spent, no SDK change authorized. Baseline `2c9d7ba7`; the tree read at `7356a0f1`.

**The answer in one paragraph.** None of the ten use cases requires a capability the SDK does not
have. The seven vault specs and both Portfolio Management products are buildable today on a
supported route, and the A2A variant as Dave re-scoped it needs nothing new: the A2A exchange between
two agents is outside the SDK contract, and the CCF part — an agent assembling a Context Product
in-process to answer a peer — is an already-proven pattern. What the pass exposes is *adoption
friction*, and Dave has ruled that a supported mechanism is not sufficient if normal adopters
repeatedly reconstruct SDK plumbing. Three shared patterns will be measured during the first batch
(mnpi, aml, ib) against an explicit rubric before any SDK change is considered: the credential-derived
policy envelope, several credentialed principals through one door, and policy-before-similarity over
a passage corpus.

---

## 1 · Population and rule

**The 24.** cp-01 through cp-14 (qualified) plus the ten below. cp-00, s1-* and hw1-* are not
counted (Dave, 2026-09-19).

| # | Use case | Source | Tier |
| --- | --- | --- | --- |
| CP-15 | `kyc-refresh-beneficial-ownership` | vault `context-products` | T4 |
| CP-16 | `abs-securitization-surveillance` | vault `context-products` | T4 |
| CP-17 | `mnpi-wall-enforcement` | vault `context-products` | T5 |
| CP-18 | `ib-opportunity-synthesis` | vault `context-products` | T5 |
| CP-19 | `aml-typology-match` | vault `context-products` | T5 |
| CP-20 | `syndicated-lending-co-lender` | vault `context-products` | T5 + cross-organization |
| CP-21 | `large-exposure-rwa-concentration` | vault `context-products` | T5 capstone |
| CP-22 | Agent-internal Context Product assembly inside a cross-process multi-agent workflow | Dave's definition, 2026-09-20 (§4.2) | — |
| CP-23 | Portfolio Early-Warning / Concentration Context | Dave's definition, 2026-09-20, from the `cbcib` requirements (§4.2) | — |
| CP-24 | Portfolio What-If / Stress Context | Dave's definition, 2026-09-20, from the `cbcib` requirements (§4.2) | — |

The CP numbers are positional labels for this document. Dave assigns ladder identities when each is
built; the build order (§9) is not numerical.

**The rule applied to every row** (Dave, 2026-09-19, verbatim in `docs/DECISIONS.md`). First ask
*"What SDK capability does this example require that CP-01–14 have not already proven?"*, then
classify into exactly one of six buckets: (1) already supported → existing path, no redesign;
(2) ergonomics/friction only → backlog unless it makes the supported path impractical;
(3) example/data limitation → record and continue, never repair the SDK for it; (4) missing
capability the use case requires → stop, smallest reusable SDK abstraction; (5) incorrect SDK
behavior → fix; (6) nice-to-have → backlog. *"A new example does not earn permission to redesign an
existing SDK mechanism simply because another design would be cleaner."* Both producer routes are
supported (LAUNCH SCOPE): the paved facade, and lower-level governed assembly plus the standard
door. Launch blocker versus backlog is decided by `docs/EXAMPLE-EVALUATION-CRITERIA.md` §C against
the core launch contract in §D; friction is measured per §E and, from this revision, per the
developer-experience rubric in §5.0.

**Standing rulings applied uniformly, confirmed by Dave on 2026-09-20 (direction item 4):**
group-scoped children rather than per-member composite fan-out; reification plus endpoint closure
as the realization of "the edge never materializes" (mnpi); invoke-time projection conditioning
(one plan per class, role-branched at `invoke`); the ledger-data route for decision-time policy
where appropriate; several product gates per class as composition today and backlog; low-road
support for aggregation shapes; dual-TTL and the other post-launch items stay post-launch; estate
limitations are never repaired through SDK changes. Products are assembled per request, never
precomputed, so a spec's *materialization posture* and any scheduler or continuous-monitoring loop
are harness- or agent-owned, outside the SDK contract.

---

## 2 · Evidence standing — three states, kept apart

The pass ran as an orchestrated workflow in two stages; a usage-credit outage interrupted both, so
the evidence carries three states and every claim below names its state.

| State | What it means | Where it applies |
| --- | --- | --- |
| **Verified** | The analyst's classification was attacked by independent verifiers reading the tree (refute-from-three-lenses on gaps, audit on "supported", challenge on "deferred") and survived or was revised | The portfolio-management placeholder analysis only (29 rows: 21 supported-class rows audited, 8 deferred rows challenged) |
| **Analyst-classified** | One analyst per use case read the spec in full, read the SDK modules named, and classified every capability with tree citations; a second pass augmented six of the nine analyses against the three capability clusters the first pass lost | The seven vault specs and the original A2A variant (368 rows) |
| **Ruled** | Dave's direction of 2026-09-20 replaces the analysis | CP-22's re-scope; the CP-23 and CP-24 definitions; the standing rulings in §1 |
| **Not analyzed** | Named by the completeness critic as a capability with no row | Nine items, listed in §10 and folded into the matrix where the disposition is not in doubt |

What was done, by count: ten capability-map clusters over the SDK (210 mechanism rows with module,
symbol, proof and known limitations); nine use-case analyses (397 rows after augmentation); one
synthesis (26 batches, 37 estate limitations, 20 questions); one completeness critic, which resolved
3,343 path citations, 691 test-node citations (1 wrong file) and 2,830 symbol citations (13 wrong
module or absent) against the tree, found 9 capabilities with no row, 14 cross-use-case
inconsistencies and 5 launch-contract items no rung carries. The critic's corrections are applied
here (Appendix A); the raw analyses are preserved unedited in the evidence tarball (§10).

**How to read a row.** *Supported* means a proven path exists on CP-01–14; *supported-unproven*
means the mechanism exists (unit- or conformance-proven) but no rung has driven the spec's exact
shape — an example obligation, not an SDK gap. Fifty-one rows are supported-unproven; the proof
batches (§5.3) absorb them.

---

## 3 · The result in one page

**Bucket distribution after augmentation and the 2026-09-20 rulings** (rows per use case; CP-22's
A2A-facing rows are outside the contract and no longer counted):

| Use case | rows | (1) supported | (2) friction | (3) estate | (4) missing | (5) incorrect | (6) later |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CP-15 kyc | 61 | 41 | 9 | 8 | 0 | 0 | 3 |
| CP-16 abs | 46 | 32 | 7 | 6 | 0 | 0 | 1 |
| CP-17 mnpi | 54 | 33 | 12 | 4 | 0 | 0 | 5 |
| CP-18 ib | 43 | 28 | 9 | 5 | 0 | 0 | 1 |
| CP-19 aml | 40 | 29 | 5 | 5 | 0 | 0 | 1 |
| CP-20 co-lender | 37 | 28 | 6 | 1 | 0 | 0 | 2 |
| CP-21 large exposure | 59 | 32 | 10 | 6 | 0 | 0 | 11 |
| CP-22 agent-internal assembly (re-scoped) | 13 CCF-facing | 11 | 2 | 0 | 0 | 0 | 0 |
| CP-23 / CP-24 PM (defined) | 29 (placeholder analysis, verified) | 17 | 5 | 1 | 0 | 0 | 6 |

**Three things the counts say.** No use case is blocked on the SDK. The bucket-2 column is where the
work is, and it is *shared*: the same seven or eight gaps recur across the T5 specs and both PM
products. The bucket-6 column on the capstone is large because it composes every primitive below it
and several of those compositions (fan-out, artifact-by-instant, durable audit) are excluded from
the launch contract by standing rulings, not by this pass.

**What changed from revision 1.** The only bucket-4 item, an A2A request/response door, is
withdrawn: Dave re-scoped CP-22 so that the A2A exchange is outside the SDK contract and the CCF
requirement begins when Agent B needs governed context and ends when Agent B holds the Context
Product (§4.2). There is no candidate launch blocker on capability. The launch concern is now
adoption friction, measured explicitly (§5.0).

---

## 4 · The matrix

### 4.1 Overview — Dave's six columns

| Use case | Capability tested (what nothing before it proved) | Existing SDK mechanism that should satisfy it | Genuinely new capability | Likely friction (measured) | Implementable today | Launch blocker vs backlog |
| --- | --- | --- | --- | --- | --- | --- |
| **CP-15 kyc** | A sub-threshold finding kept *inside* the product and handed to the SDK `ReviewQueue` with the served content address as `output_ref` (first product-side HITL composition); per-person resolution confidence as a claim attribute end to end; multiplicative ownership with the revisit cap disclosed; a request default *per entitlement*; evidence-anchored 24 h TTL over a sanctions publish date | Paved road (`open_product` + `open_door`); `src/ccf/hitl/review_queue.py` (`ReviewQueue`); `RelationshipClaim` attributes; cp-04-canonical circuits and s1-01 ownership recursion as Π precedents; the `PolicyConstraintResolver` seam; `from_entity_freshness` | none | Second instance of acquisition-seam entitlement glue (~60 lines); readers restated (~150 lines, 6th tree); passage cite/re-hash copied (~70 lines, 2nd); ReviewQueue composition = 4 injected objects + 1 policy artifact + a `LineageEntry` per flagged person + an undefined product-scoped `workflow_state_ref`; three spec gates in one slot; fractional parameters as decimal text | Yes on the paved road; partial for the review-queue convention (Q14) and for the 24 h anchor on a snapshot (illustrative window under D-IMPL-323) | Backlog (9 friction rows); no blocker |
| **CP-16 abs** | Granularity as a governed cost-and-shape lever: an enum parameter with a role-applicable `allowed_set` ceiling that refuses `loan` by name; first class combining an evidence-anchored TTL with a decision-instant parameter (residual 341-1 goes live); loan grain without materializing a 1.3 M-row pool; trigger thresholds anchored by passage re-hash | `ArgumentDomain.members`; `PolicyConstraint` + `ConstraintApplicability.perspective_role`; `decision_instant_parameter`; `resolve_ttl_anchor`; `PassageAnchor`; paved road, low road reserved for loan grain | none | Applicability by role, not principal (2 principals → 2 roles + 1 constraint + ~2 glue functions for the second principal at the door); the spec's "lower and disclose" gate recast to refuse-by-name; request schema and cost note reach no caller (24.7-C-01); date-typed `as_of` as decision instant is an unmeasured serve-time risk; three estate tables duplicate the Control Plane ceiling; six spec operators map to three keys; three readers; two gates, one slot; 24 h TTL vs monthly data | Yes (32 supported + 5 supported-unproven of 46 rows) | Backlog (7); spec gate recast (Q18); no blocker |
| **CP-17 mnpi** | Entitlement as a *formative* constraint sourced from the credential: one address, three credentials, three structurally different products whose bounding sets come from the grant; bitemporal wall state; a supersede-only half-life in a served product; the Reg FD *widening* supersession as admission; the departmental SQLite restricted list read first; no disclosure including the SDK's own marker channel | `open_door` overrides (`token_verifier`, `entitlement_source`, `perspective_resolver`); `ProductEntitlementPolicy` with N grants; `PolicyFilter` formative substitution + GQ-16 endpoint closure (reification — **ruled the accepted realization**); `AcquisitionContext.perspective`; the invalidation register; supersede-only decay; `ComputedEmptyFinding` + disclosure | none (Q7 resolved by ruling; Q8 is a measurement) | Three principals need 3 override objects and one ordering rule (`open_door` registers a one-principal policy unconditionally; latest-wins shadowing); per-principal sets only at the acquisition seam (2nd rewrite of cp-13's glue); edge vocabulary via reification + 1 containment gate; one `plan_id` with a role branch (**ruled sufficient**); requested perspective on HTTP only; a `perspective` argument is accepted and never honored; `known_as_of` as deployment glue; first SQLite source | Partial-to-yes on the paved road | Backlog (12); the three-principal door is measured in batch 1 (§5.0) |
| **CP-18 ib** | Π as a dimension of the product on a *consumer-anchored* subject: a policy-versioned, perspective-selected weight vector pinned in lineage so a ranking replays under the prior version; three orderings from identical signals through one class and one door; wall state inherited from mnpi; banker-local SQLite notes as claims that move a ranking | Opaque `ProductRequest.subject`; `ProjectionPlan.invoke(perspective=)`; the manifest pin (`pins.version_for`) into `policy_bundle_versions` and replay dimension 2; the adopter `policy` section as the only pinned slot; `PerspectiveResolverProtocol`; `PolicyFilter` structural absence; `EnvironmentDocument.sources` | none | 40 bankers under 3 perspectives through one door = 2 typed overrides or a hand-registered 40-grant policy (composition with the door's own registration unproven); weight vector pinnable only inside the policy bundle (66 Decimal strings; cp-07's disk-read projection is the silent counter-pattern); wall exclusion glue, 3rd writing; one permitted set across all mapped classes; 4 invariants, 1 slot; passage retrieval outside the operator; payload nesting ceiling | Partial-to-yes | Backlog (7 bucket-2 candidates); measured in batch 1 |
| **CP-19 aml** | Whitepaper §7.4(c) — four-operator policy-before-similarity on a domain rung as a *served operator-plan fact*; a filing posture in force at a past `as_of`; three perspectives differing in what is assembled; SAR confidentiality read from SQLite before anything runs | `CATEGORY_ORDER`; `SimilaritySelect`, `PolicyFilter`, `TemporalAsOf`; `build_operator_registry` → `TokenOverlapIndex`; `constraints_in_force` effectivity windows; `open_door` overrides; disclosure layer | none; two bucket-2 candidates (a request-bound Similarity query; the credential envelope, 3rd writing) | As mnpi, plus: posture windows derived by the deployment (2 glue functions); one permitted set across four classes; five invariants, one slot; four readers | Yes on the paved road with the lexical index; the vector path is blocked by the estate (72 advisory passages carry no embedding) and no shipped embedder | Backlog; Q5 on the Similarity query; build after mnpi |
| **CP-20 co-lender** | A composite admitting a child produced by a *second deployment of another organization* under a negotiated asymmetric envelope; the peer-declared TTL flooring the composite (first live carrier of residual 341-4); remote-attested vs local-reconstructible provenance kept apart; the peer's agent as a second credentialed principal | Route A `mcp_product` (the cp-14 chain: `McpProducerRegistration`, `QuestionBoundChildResolver`, `CompositeAdmissionGate`, D-IMPL-340 proofs); Route B peering (`PeeringAdmissionGate` with the consumer-tenant stamp, `DetachedJwsIdentityProvider`, `PeerTrustGrant`, `verify_child_eligibility`, `LfA2AWire`/typed HTTP, `build_children=` hatch); `compose_expiry`; federated TTL vs consumer `MAX_TTL`; `PolicyConstraint` effectivity for competition-law rules | none | Route B is not declarable (no peering section in the deployment config or binder; 89 hand-wired consumer lines on the archived example); a second full producer tree over the peer estate; five SDK-internal rules with no public page; two credentialed principals at one door (~15–25 lines of overrides); `include_federated` needs a second class or a `build_children` wrapper; list-envelope containment is glue; the envelope maps to three SDK identities across two deployments; latency and attestation are *declarations* in the peer's data | Yes on Route A end to end; partial on Route B; the estate is ready (ccf-dataprep 2026-09-19) | No blocker. One route decision and two spec-versus-ruling conflicts before Gate 1 (Q17); Route A recommended |
| **CP-21 large exposure** | A composite over a derived connected group (N anchors) with the group moved by `connection_basis`; regime as a policy envelope at `as_of`; an object-valued `proposal` computed with and without; worst-of inherited debt with tolerance fail-closed; three perspectives; four stores including the SQLite limit workbook; examiner replay | `ChildRequirement` (one requirement per class, one subject per question — **group-scoped children, ruled**); `CompositeAdmissionGate`; `compose_expiry`; `compose_debt_factors`; the cp-14 chain; regime versions as ledger data cut by `TemporalAsOf` (**ruled where appropriate**) or as `PolicyConstraint` artifacts; one closed object level on `SkillArgumentProperty`; low road + standard door for a group-scoped exposure producer | none (Q13 resolved: group-scoped children) | The supported path needs 1–2 *new* group-scoped producer trees (the frozen cp-05 door pins its instant and threads no families); two instants and only `asked_at` reaches constraints; three principals via overrides; one gate for three; four readers; regime-as-data does not move `policy_version` | Partial — buildable as a composite over group-scoped children; a composite behind a door is unproven | Not a blocker; the group-scoped producers are example work to authorize at Gate 1 |
| **CP-22 agent-internal assembly** | An agent (Agent B) that participates in a normal cross-process multi-agent workflow — Agent A asks it over A2A — answers by assembling a governed Context Product **in-process**, extracting the use-case-specific answer, and replying over A2A, without Agent A knowing CCF exists. Nothing before it proved CCF used *inside* an agent that is itself a server in someone else's protocol | The proven in-process assembly pattern: the client library's `inprocess` binding (`examples/hw1-companies-over-revenue`, `consume.py`) or `open_product` on the paved road (cp-04-canonical) inside Agent B; Agent B's own principal entitled at the resolver; the served product's replay record and debt from `GovernedResolver`; the harness's A2A server (ADK's native A2A support, or `a2a-sdk` directly) is harness-owned | **none** — by ruling: no A2A Context Product door, no `peering_product` skill, no identity parity across MCP and A2A, no new A2A SDK capability | Two bucket-2 items: the in-process consumer still hand-assembles its replay environment (CP06C-F-01 recipe); the `inprocess` binding and `open_product` are not on a public page (B5). Everything about A2A hosting, cards and admission is outside the contract | Yes, today, with no SDK change | No blocker; no batch A8 |
| **CP-23 Portfolio Early-Warning / Concentration** | One governed product over *many* anchors — a PM's book — aggregating six signal families (utilization/headroom, rating migration, covenant pressure, collateral deterioration, liquidity/exposure, external signals) into policy-conditioned portfolio views with severity-tiered, actionable early-warning signals; signal freshness per class; worst-factor debt over N members; per-member serve-time invalidation; concentration against declared limits | Low road (governed assembly + standard door, cp-05 shape; **ruled** for aggregation) over a group-scoped member set; `compose_debt_factors`; `run_gates(touched_entities)` for per-member invalidation; `HalfLifeEntry` per signal class (cp-09/10/11/12 proofs); `invoke(perspective=)` for PM / credit-officer / RM views; severity tiers as a Control Plane threshold artifact (values); `build_egress_server` or `open_door` overrides for several roles | none | Low road cost (cp-05: 2,382 lines over 5 files vs cp-04-canonical: 1,102); the book's member list as an array parameter with no domain shape and order-as-identity; limit and headroom arithmetic has no SDK home (would be the 3rd instance after cp-05 and the capstone); capital base and limits in three stores under different names; `touched_entities` must enumerate every member or the invalidation gate passes silently (A10); six per-anchor mechanisms already proven separately (cp-05/06/08/09/10/11) re-composed at book grain | Yes on the low road; the scheduler loop and alert clustering are harness/agent-owned | No blocker; measured under §5.0 as the first low-road rung; Q16 resolved by modeling membership as an entity attribute |
| **CP-24 Portfolio What-If / Stress** | A scenario product: current governed context plus *explicit hypothetical parameters* ("SOFR +150 bps and CRE values −10%") projected into utilization, coverage, collateral and loss impacts; policy/role-conditioned views; lineage that separates observed evidence from scenario assumptions; replay of the scenario to the same address | The request contract's object parameter (one closed level, `SkillArgumentProperty.properties`) for the `scenario`; Π as deterministic arithmetic over a Control Plane sensitivity artifact (values); observed facts carry source lineage, assumptions are the recorded effective request (replay dimension 2) and the request on dimension 5 — the separation exists by construction; `replay` re-feeds the recorded request; CP-23's book context as the current-state input (group-scoped, low road) | none | An object parameter has crossed no shipped door and a nested fraction has no exact wire form (B7); the payload must label scenario-derived measures (payload design); many scenarios are many requests (per-request assembly, by ruling); rate and collateral sensitivities are illustrative artifacts to disclose under D-IMPL-323 | Yes on the low road once CP-23 exists; estate readiness for rate curves and collateral valuations to be probed at Gate 1 | No blocker; the Digital Credit Twin loop stays harness-owned |

### 4.2 Definitions and per-row notes

**CP-22 — re-scoped by Dave (2026-09-20).** The use case is a developer's multi-agent workflow:
Agent A collaborates with an external Agent B over A2A for a banking answer. That exchange is two
agents communicating across a process boundary and has nothing to do with the SDK. Agent B, to
answer, assembles a Context Product directly and in-process — no MCP server — using the pattern
already proven and demonstrated; it then extracts what Agent A needs, which is use-case specific and
involves only A2A. The CCF requirement begins when Agent B needs governed context and ends when
Agent B holds the Context Product. Therefore: no A2A Context Product door, no `peering_product`
skill, no requirement for Context Product identity parity across MCP and A2A, no new A2A SDK
capability, and no batch A8. **What CP-22 proves:** that an agent participating in a normal
cross-process multi-agent workflow can use CCF internally without the other agent knowing CCF
exists. The CCF-facing rows that remain are all bucket 1: in-process assembly (the `inprocess`
binding hw1 already runs on both routes, or `open_product`), Agent B's own principal entitled at the
resolver, per-request assembly at Agent B's `asked_at`, Context Debt and the replay record written by
`GovernedResolver`, reconstruction from the record. The rows revision 1 carried about A2A hosting,
cards, ceilings, admission, tenant stamps and transport identity are outside the contract and
are dropped from the count. Base product: `examples/hw1-companies-over-revenue`, whose two-transport
consumer already isolates the in-process route. The harness side — ADK's native A2A server and
client, or `a2a-sdk` used directly by Agent B — is the developer's choice and the example should
show one, not build an adapter.

**CP-23 — Portfolio Early-Warning / Concentration Context (defined by Dave, 2026-09-20; source:
`references/cbcib-portfolio-management-CLAUDE.md`, the requirements of Dave's `cbcib` Portfolio
Management POC on GitHub, whose working branch is not yet committed).** *Subject:* a portfolio — a
PM's coverage book by default (`coverage_assignment` in `ccf_v2`, 1,000 rows, banker → client),
with an explicit `members` override; membership is modeled as an entity attribute on the member
claim, not as an edge, so per-member supersession reaches the invalidation register (the "entities
only for v1" ruling in D-IMPL-334's ruling table; this settles Q16 without lifting the limb).
*Principals:* portfolio manager, credit officer, relationship manager — three role-conditioned
views of one class. *Question:* the book's proactive-monitoring state — utilization and headroom
deterioration (facility commitment, outstanding balance, undrawn availability, drawdown velocity),
rating migration (cp-10's pattern), covenant pressure (cp-08's), collateral deterioration (cp-06's),
liquidity and exposure (cp-09's and cp-05's), external signals (cp-11's warning, adverse-media and
sector signals) and concentration against declared limits — aggregated at book grain with
severity-tiered signals whose thresholds are a Control Plane artifact (values), a per-signal-class
half-life table, worst-factor Context Debt over the members, and per-member invalidation.
*Mechanisms exercised, from the requirements' own list:* multi-anchor/group assembly, aggregation,
policy-conditioned portfolio views, signal freshness, worst-factor debt, proactive alerting.
*Out of the SDK by ruling:* the continuous-monitoring loop (harness/agent-owned; the product is
assembled when invoked), ML alert clustering, the narrative layer. *Estate:* the six per-anchor
signal families exist and are proven by cp-05/06/08/09/10/11 at one anchor; the snapshot needs an
illustrative calibration for the fast half-lives (cp-11 measured 48 of 50 anchors in the sweep band
naive, 3 of 50 with supersession applied), disclosed under D-IMPL-323; world-time `validFrom` on
superseding claims is required or every boundary is ingestion time (the CP11-F-10 shape).

**CP-24 — Portfolio What-If / Stress Context (defined by Dave, 2026-09-20; same source).**
*Subject:* the same book (or one client). *Question:* "What happens to this portfolio if SOFR rises
150 bps and CRE values fall 10%?" — the requirements' Digital Credit Twin and portfolio-wide stress
simulation. *Parameters:* an explicit `scenario` object (rate shift in basis points, collateral value
shift by asset class, optional horizon) as declared request arguments; the observed state comes from
the governed current context (CP-23's book context or its sources). *Mechanisms exercised:*
governed current context plus explicit hypothetical inputs; projection (deterministic Π arithmetic
over a declared sensitivity artifact — DSCR and interest coverage under the rate shift, LTV and
borrowing-base under the collateral shift, headroom and expected-loss impacts as illustrative
values); policy/role conditioning (which impacts each role sees); **lineage separating observed
evidence from scenario assumptions** — by construction, observed facts carry source lineage through
`L` while the assumptions are the recorded effective request on replay dimension 2 and the request
on dimension 5, and the payload labels each scenario-derived measure; **replay of the scenario** —
`replay` re-feeds the recorded request, so the same scenario reconstructs to the same content
address. *Out of the SDK by ruling:* the interactive sandbox and any scenario scheduler (many
scenarios are many requests). *Friction to measure:* the object parameter's wire form (B7); the
sensitivity artifact as a Control Plane value with its own version lane so a changed sensitivity
changes `policy_version`.

**CP-15 kyc.** The headline is a proof, not a mechanism: `ReviewQueue.submit_for_review` and the
transport, two delivery surfaces and the replay landing are unit-, workflow- and cross-process
proven, but no active example composes a HITL primitive with a *product*. The one convention to rule
at Gate 1 is what a product-scoped review passes as `PendingHitlEvent.workflow_state_ref`
(recommended: the served record's replay reference) and that the product's own record carries
`NO_HITL_ACTIONS` by construction, the human verdict landing on a second record linked by the
content hash (Q14). A same-day sanctions addition is honored on re-serve by the invalidation gate
(supported); an ownership *change* reaches the register only when the reified ownership node is an
entity claim, because relationship supersession never calls the sink (`src/ccf/graph/_writer.py`
(`upsert_relationship`)); the spec's second prerequisite has no canonical producer to require (cp-01
is a frozen specimen), so the rung reads the reference rows itself.

**CP-16 abs.** The spec's "if policy lowered the granularity, say so" cannot be authored as written:
the constraint layer refuses an out-of-bound value by name with the bound attached and never narrows
it (D-IMPL-251); the honest recast is "a request above the role's ceiling is refused
`not-in-allowed-set` carrying the bound; a served product states its effective granularity" (Q18).
Loan grain must aggregate and sample in acquisition before envelopes are emitted, or read the
pre-aggregated cohort rows — the fabric-side cost curve has never been measured on any rung.
Residual 341-1 becomes live for the first time: acquisition must be bounded at the decision instant,
a rule stated nowhere public.

**CP-17 mnpi.** Three of the spec's mechanisms are realized differently from its wording and are
disclosed rather than repaired, now by ruling: the edge vocabulary via reification and endpoint
closure; `projection_plan_id` per perspective as one `plan_id` with a role branch answered from
replay dimensions 5 and 4; and "perspective requested but refused, not downgraded" exercisable over
HTTP only. The Batch Enrich step (§D step 6) had no row; it is bucket 1 on the cp-13-canonical
precedent. The §F "ranking difference" measurement is structurally zero under the reference
per-candidate index — a property of the SDK's reference substrate, recorded as backlog, not an estate
limitation. Estate: the per-principal edge types the estate's projection plans name match none of
the 181 predicates in `fibo-v2`; the relationships exist as Postgres rows.

**CP-18 ib.** The only pinned adopter slot is the `policy` section of the deployment config, so the
weight table must live inside the policy bundle and Π must read it through a late-bound Control
Plane closure; supported, unproven by any rung, and the correct route (cp-07 reads its weights from
disk, which never reaches `policy_version`). Reg FD is inherited from mnpi's versioned binding.
Build after mnpi and compose its wall state as a governed child.

**CP-19 aml.** The per-alert similarity query has no home: `SimilaritySelectParameters.query` is an
artifact literal with no request-bound arm, so the SDK operator can rank against a class-level
typology vocabulary while the per-alert match rides the `matchesTypology` traversal, or the rung
ranks acquisition-side and leaves the headline undemonstrated (Q5, measured in batch 1). BSA/AML
program rules fold into the permitted-disposition row.

**CP-20 co-lender.** Route A (`mcp_product`) is recommended as the governed spine: the qualified
cp-14 chain carries a *question* to a registered producer, identity held to registration,
cross-tenant by design. Route B (peering) carries a signature and producer-attested eligibility but
is push-only and not declarable on the paved config; with CP-22 re-scoped away from peering, nothing
in the first batches exercises Route B. Two spec statements contradict standing rulings and must be
amended at Gate 1, not built around: `require_attestation=false` is unexpressible (D-IMPL-16), and
"an unattested remote claim is recorded as Context Debt rather than admitted" contradicts D-IMPL-336
F1 (a refused child refuses the composite even in an optional slot) — the SDK's outcome for the
NULL-attestation declaration is a governed refusal, which `docs/EXAMPLE-EVALUATION-CRITERIA.md` §A
names a success. `max_federation_latency` exists as one environment-level deadline, not a
per-request parameter; the peer's `declared_latency_ms` is a declaration the projection compares.
Estate, as ccf-dataprep states it (vault `contrib/ccf-dataprep/co-lender-peer-estate-as-measured`,
2026-09-19): one peer fabric holds both counterparties (Fluree `:8091` ledger `bofa/syndicate`;
Postgres database `bofa_syndicated`, schema `colender`; Mongo `bofa_syndicated` empty by design);
RSSD identity and Call Reports for 16 of 45 members; own position for 5 of 12 facilities;
credentials only in Dave's shell exports.

**CP-21 large exposure.** Group-scoped children are the ruled path: one exposure question over the
member list (cp-05 already answers a family from one anchor), collateral over a borrower list,
covenant group-scoped or optional. That means one or two new group-scoped producer trees on the low
road before the capstone can be declared — example work to authorize at Gate 1, and shared with
CP-23 (the same limit and headroom arithmetic, written once). Regime at `as_of` takes the
ledger-data route by ruling where appropriate. Estate rows added: FFIEC 101 never fetched, no FR
Y-9C base; no connected-group registry (groups are derived components); economic-dependency author
and date are node literals.

---

## 5 · Batches by shared capability gap

### 5.0 The developer-experience rubric (Dave, 2026-09-20) — a launch concern, measured explicitly

*"A supported mechanism is not sufficient if normal adopters repeatedly have to reconstruct SDK
plumbing."* For CP-15 through CP-24, every rung's close report measures, with counts:

1. domain/business lines of code;
2. SDK/plumbing lines of code;
3. copied integration patterns (which helper, copied from which tree);
4. hand-built Control Plane or runtime objects (constructed in code rather than declared);
5. use of private or internal SDK symbols;
6. configuration duplication (one value stated in two authorities);
7. concepts not discoverable from public SDK documentation;
8. whether an AI coding agent could reasonably generate the implementation from the Context Product
   spec plus public SDK guidance.

Each pattern is then classified: **easy or generated** → keep the existing path; **repetitive but
understandable** → backlog; **substantial repeated plumbing or private knowledge** → candidate SDK
ergonomics issue; **correctness depends on hand-wiring** → launch concern. Three independent
implementations of the same plumbing pattern trigger an *abstraction review*, not an automatic
abstraction. Nothing in A1–A7 or A10 is implemented before that review.

### 5.1 The shared patterns, re-evaluated under the rubric

| | Pattern | Shared by | Rubric class (prediction, to be measured) | What batch 1 measures |
| --- | --- | --- | --- | --- |
| **A1** | Several credentialed principals through one standard door: `open_door` registers a one-principal policy unconditionally and shadows (latest-wins) a deployment's multi-principal policy; the alternative is three typed overrides in code | 8 (mnpi, aml, ib, abs, kyc, large exposure, co-lender, CP-23) | **Correctness depends on hand-wiring** for the shadowing half (a policy registered in the wrong order is silently replaced — a serve-time shell, no boot refusal); *substantial repeated plumbing* for the override trio | On mnpi: hand-built objects (predicted 3), the ordering rule as private knowledge, configuration duplication between the door's derived grant and the tenant policy; whether an AI agent would discover the override trio from `public/` (it is not documented there) |
| **A2** | Credential-derived policy envelope: a permitted set or a request default sourced from the verified grant. **Determination (Dave asked):** the *values* — which classes, jurisdictions or corpus a role may see — are legitimately product-specific policy, and they already have a governed home: a `PolicyConstraint` with `perspective_role` applicability and `allowed_set`, whose bound reaches the Policy operator through `RequestBoundParameter` with dimension-2 provenance when the caller states the parameter. The *plumbing* is what repeats, and it is SDK plumbing, not policy logic: (i) filling an omitted parameter from the grant — no constraint operator does it (`preferred` folds to guidance and never fills), so each rung writes a deployment `PolicyConstraintResolver` or acquisition-seam glue (cp-13's one dataclass, three functions, two exception classes, refusing by raise); (ii) containing a *list* parameter element-wise (`_refuse_against` folds scalar membership only) | 8 (mnpi, aml, ib, kyc; abs, large exposure, co-lender, CP-23 for the default half) | **Substantial repeated plumbing plus private knowledge** → candidate SDK ergonomics issue. The smallest closure, if the review confirms it: a role-applicable *default* arm on the existing `PolicyConstraint` (an omitted parameter filled with authority `policy` and the constraint as provenance) plus the element-wise fold (B1) — same artifact, same pin, no new seam | On mnpi (2nd instance) and aml (3rd → abstraction review): plumbing LOC of the envelope, whether the values sit in a declared artifact or in code, private symbols touched, whether the refusal is governed or raised; on ib and kyc the same count |
| **A3** | Policy-before-similarity over a passage corpus with a request-bound query and a pinned index: the SDK operator ranks graph entities from a lexical index over entity attributes with a class-level literal query; no vector substrate is wired by the builder and no embedder ships; cp-13-canonical's acquisition-side retrieval (no index pin, Similarity absent from the plan) is the copy | 7 | **Substantial repeated plumbing plus private knowledge** → candidate SDK ergonomics issue; three separable closures if confirmed (a `RequestBoundParameter` arm on the query; a passage-corpus source for `SimilaritySelect`; per-match score on the output) | On mnpi and aml: copied retrieval helper LOC; whether the served plan names Similarity; whether the index and model version are pinned; the un-embedded share of the corpus each rung meets |
| **A4** | Policy and evidence at the decision instant when `as_of` ≠ `asked_at` | 7 | **Repetitive but understandable** → backlog. The ledger-data route is ruled acceptable where appropriate; the deployment resolver is the ruled seam; the date-typed `as_of` boot refusal is a small hardening; residual 341-1 stays a documented limitation | Count only: which route each rung takes and how many lines it costs |
| **A5** | Several declared product gates per class | 7 | **Repetitive but understandable** → backlog, by ruling (composition today) | Count: invariants folded per class; whether the refusal's detail string is what a consumer sees |
| **A6** | A policy-emptied view served with a marker naming the policy operator | 6 | Not plumbing — **one measurement** before the wall rungs build. If the marker reaches an unentitled principal below full disclosure, correctness depends on a deployment gate every wall rung must write → launch concern | The one test (Q8), before mnpi's Gate 1 |
| **A7** | Per-perspective projection-plan selection (D-IMPL-49 drift) and pinned Π parameters | 6 | **Easy / keep the existing path**, by ruling (invoke-time conditioning); the distinct plan id per perspective is backlog | Count: the bundle-pinned weight route's LOC on ib |
| **A10** | Low-road obligations that pass silently: `run_gates(touched_entities=None)` passes with no signal; the pre-acquisition refusal is raised, unrecorded (residual 304) | 4 (large exposure's group producer, abs at loan grain, CP-23, CP-24) | **Correctness depends on hand-wiring** → launch concern candidate; one guard closes the silent pass if the review confirms | On the first low-road rung (CP-23): whether the builder threaded `touched_entities`, and what an omitted set does |

**Withdrawn by ruling.** A8 (A2A request/response door) — CP-22 re-scoped; no A2A capability is
owed. **Deferred.** A9 (producer-side replay on the peering emit path) — no first-batch rung takes
the peering route; it stays a recorded candidate for the co-lender's Gate 1 if Route B is ever
chosen (Q6 deferred with it).

### 5.2 Backlog by existing ruling (§I records; proceed on the supported path)

| | Gap | Shared by | Supported path today | Record |
| --- | --- | --- | --- | --- |
| B1 | Element-wise containment of a set-valued request parameter by a role-applicable `allowed_set` | 7 | a seam intersection per deployment; the peer enforces its own envelope on the co-lender route | D-IMPL-253 Q4; array order is identity, no array domain shape |
| B2 | Requesting a perspective over MCP, and the `perspective` argument shadow (accepted, never honored; only `intent` has a boot refusal) | 5 | HTTP `?role=`; MCP derives the role from the grant | D-IMPL-260 P-D, D-IMPL-264 D-01 |
| B3 | Declared-but-unread Control Plane values: `HalfLifeEntry.supersession_event` is a required label no mechanism reads; `FreshnessSLA.max_age_seconds_by_signal` is judged only at bind time | 7 | declare as documentation; "event-driven" is `decay: supersede-only` | D-GATE-cp-08, D-IMPL-331/332/333, D-IMPL-106 |
| B4 | Deployment declaration for a peering leg (endpoint, card, ceiling, trust) with a facade | co-lender Route B only, now | driver code and the test fixture | D-IMPL-136/137, D-IMPL-141 |
| B5 | Adopter-facing public pages for the policy, temporal/invalidation/replay and composite clusters (zero public pages for entitlement, disclosure levels, `PolicyConstraint`, `RequestBoundParameter`, operator order, the gate slot, supersede-only, relative defaults, the decision instant, `ReplayBinding`, the invalidation register, `open_door`, `build_egress_server`, the `inprocess` binding, `open_product`); the tutorial and two how-tos literal-include retired examples | all | source docstrings and `docs/DECISIONS.md` | Rubric measure 7 and 8 will quantify it per rung; **Q20** asks whether the package is launch scope |
| B6 | Hand-rolled per-store readers restated per tree (SPARQL over httpx, psycopg, pymongo, sqlite3) | all | `AcquireProtocol` / `AcquisitionContext.sources` by env-var name | D-IMPL-277 OPEN, D-IMPL-282 R-09 (ruled discoverability) |
| B7 | Request-surface wire facts: fractional parameters as decimal text; an object parameter has crossed no shipped door and a nested fraction has no exact wire form; argument names restated as string constants; `policy_overrides` unreachable through either door; the technical capability re-read from YAML | all | proven per item at unit or wire level | D-IMPL-302, D-IMPL-103, CP04C-F-03, CP14-F-21 |

### 5.3 Proof batches — no SDK change; an example must simply drive it

| | What no rung has proven | Carried by |
| --- | --- | --- |
| P1 | A HITL primitive composed with a Context Product: `ReviewQueue` with the served content address as `output_ref`; `ExceptionEscalation` on a computed breach; the human action on replay dimension 2 | kyc (headline), aml, mnpi, large exposure, CP-23 |
| P2 | Supersession compositions: a *widening* supersession as admission; a principal-scoped wall crossing invalidating only products that touched it; per-member invalidation of a multi-anchor product through the real writer → register → gate path | mnpi, ib, abs, large exposure, CP-23 |
| P3 | Composite and cross-deployment proofs: a composite served through the standard door or HTTP route; a child arriving over a wire flooring the composite's expiry (residual 341-4); a two-tenant, two-credential `mcp_product` admission; the first optional requirement priced at completeness-when-absent; the first registered `ccf.policy-constraint` from estate rows; the first non-default disclosure posture on a grant | co-lender, large exposure, abs, aml, kyc |
| P4 | CCF used inside an agent that serves another agent's protocol: in-process assembly within an A2A-served agent, Agent B's replay record and debt, no CCF knowledge on Agent A's side | CP-22 |
| P5 | A scenario product: an object parameter through a door; observed-versus-assumed lineage in the payload; replay of a scenario to its address | CP-24 |
| P6 | Multi-anchor low-road aggregation: worst-factor debt over N members, per-member invalidation, three roles over one book | CP-23 |
| P7 | The fifty-one supported-unproven rows: the first `allowed_set` + `perspective_role` constraint (abs); a request-bound permitted set on a T5 rung; passage similarity through the SDK operator; the first departmental-SQLite source; one-address-three-products; a policy version pinned through the bundle (ib) | every rung |

### 5.4 Exclusions and the repeated-glue register

**Excluded from launch by standing ruling, confirmed 2026-09-20** (bucket 6): fan-out under one
composite (N children of one class, concurrent dispatch, a per-request federation deadline —
D-IMPL-343 B-20); discovery of a class's request surface before asking (D-IMPL-264 amendment 1 F-5);
examiner-facing re-execution over an Experience surface and a durable audit plane (residuals
341-2/341-3 carried); Control Plane artifact versions selected by a past instant; an assertion-time
request axis; relationship-grain invalidation (the PM definitions avoid it); dual-TTL (CIF-G15).

**Repeated glue, by family and instance count** (`docs/EXAMPLE-EVALUATION-CRITERIA.md` §H; under the
rubric, the third independent implementation triggers an abstraction *review*): acquisition-seam
entitlement glue — cp-13-canonical today, mnpi second, aml third (→ A2 review); passage retrieval
plus cite/re-hash/anchor — cp-13-canonical today, owed by six (→ A3 review); the
no-disclosure/containment predicate — cp-01, cp-02, cp-11 today, owed by four (→ A5, A6); per-store
readers — five trees measured, owed by seven (→ B6, ruled); the replay environment — ~40 lines per
producer plus one private reach, ruled recipe-not-seam (CP06C-F-01), now also CP-22's and CP-23's;
circuit enumeration and multiplicative ownership — cp-04-canonical and s1-01 today, kyc second;
limit and headroom arithmetic — cp-05 today, CP-23 second, the capstone third (→ review).

---

## 6 · Coverage holes in the 24 — launch-contract items no rung carries

Which `docs/EXAMPLE-EVALUATION-CRITERIA.md` §D items are exercised by neither CP-01–14 nor any
remaining use case, after the 2026-09-20 rulings:

1. **"acquire products through … local callables, fixed MCP resources"** — the local-callable and
   fixed-MCP-resource skill legs are exercised by no active example and no remaining use case; the
   skill-type tokens occur only in the banking test fixtures and the archived examples. Owner rung or
   an explicit determination needed.
2. **The composite floor bound by a child arriving over a wire** (residual 341-4) — carried only by
   the co-lender.
3. **An optional requirement priced at completeness-when-absent** — unit-proven only; only the
   capstone would declare one.

Withdrawn from the list: "identity across A2A" — no parity requirement exists after CP-22's re-scope.

---

## 7 · Estate limitations — recorded, disclosed where the reader meets them, never repaired in the SDK

Every figure is from the ladder survey (2026-08-28), the store catalog (2026-08-31), the read-only
census of 2026-09-19, or ccf-dataprep's instruments; dates are cited because the estate is live.
Three of the seven products (kyc, abs, mnpi) still have no manifest in ccf-dataprep's coverage
validator; aml (16 PASS), co-lender (16 PASS with the peer configured), ib (12/5/1 GAP) and large
exposure (12/4/1 GAP) are probed. CP-23 and CP-24 readiness (rate curves, collateral valuations by
asset class, the book roster) is to be probed at their Gate 1.

- **Snapshot versus fast half-lives, every product.** Sanctions ~1 day (kyc), transactions ~1 hour
  (aml; newest value date 2026-08-24), positions ~1 hour and the restricted list ~1 day (mnpi),
  spread ~1 day (ib), exposure ~4 hours (large exposure; balances 324–396 hours old), servicer data
  monthly against a 24 h TTL (abs), book signals for CP-23: each needs an illustrative calibration
  disclosed at every site under D-IMPL-323's four conditions, or a pinned historical `as_of` where the
  spec makes `as_of` a parameter. Never by moving `asked_at` silently.
- **Passages without embeddings.** 14,289 of 37,865 passages (37.7%) carry no usable vector; the 72
  FinCEN advisory passages (aml) carry neither embedding nor sha256; the 476 regime and methodology
  passages (large exposure) all carry vectors. cp-13-canonical's `not_evaluable` disclosure is the
  supported reading.
- **Vocabulary divergence from the specs.** `controls` carries no assertions (kyc, mnpi);
  `collateralizes`/`subordinateTo`/`triggeredBy` as spelled do not exist (abs uses the FIBO terms;
  two trigger classes sit in Provisional FIBO modules); `identifiedAs`/`sameAs` are 74 reified
  resolution nodes (kyc); `beneficialOwnerOf`/`relatedAlert` are the FIBO IRI and a Postgres link
  table (aml); the mnpi per-principal edge types match none of the 181 predicates; `participatesIn`
  is deliberately not minted — the share lives on 97 reified participation nodes (co-lender);
  residency constraints name countries while parties carry ISO3 (aml).
- **As-of over the Fluree HTTP path silently ignores the ledger `t`** (ccf-dataprep known-issues
  §51); only the SPARQL `FROM <ledger@t:N>` form cp-08 uses is honored, and it is deployment SPARQL —
  the fabric's own snapshot pin is what replay resolves (D-IMPL-88). Every "state at `as_of`" row
  derives its answer from effective-date literals. Date literals stay untyped (§59); loaders are
  never re-run (§13.3).
- **Thin positive classes, honest not defective (§J).** One engineered trigger amendment and one
  vintage cell with two deals (abs); 18 MNPI-bearing interactions and one Reg FD event (mnpi); 24
  typology matches and one near-match (aml); one insider designation, 4 economic-dependency edges
  (large exposure); 4 restricted-list rows all still active (ib, mnpi); every sanctions match
  synthetic by construction (kyc); cp-11 found 3 of 50 anchors in its warning band with supersession
  applied (CP-23's sweep will be thin the same way).
- **Missing halves the specs assume.** No banker-to-perspective table (ib); wall crossings keyed to
  the mnpi principals, not to bankers (ib); the S-1 half of the registration pipeline (ib, GAP);
  FFIEC 101 and FR Y-9C (large exposure, GAP); no connected-group registry (large exposure); blackout
  windows have no type or predicate (mnpi); RSSD and Call Reports for 16 of 45 syndicate members, own
  position for 5 of 12 facilities, no amendment announcement dates (co-lender);
  `counterparty-reference-snapshot` has no canonical producer to require (kyc).
- **Frozen specimens are not usable as children.** The frozen cp-05 door pins its instant and threads
  no families (CP05D-F-01), so the group-scoped exposure producer is new; cp-01 fails construction on
  the current SDK.
- **The peer estate** (ccf-dataprep states, 2026-09-19): two counterparties on one fabric; three
  engineered conditions are declarations in data (band-only disclosure, `declared_latency_ms` 7200
  against a 10,800 s TTL, a NULL attestation); MongoDB empty by design; isolation is software-only;
  the isolation validator collects zero tests under pytest and must be run as a script.

---

## 8 · Open questions — what the rulings settled and what remains

**Settled by the 2026-09-20 direction.** Q1 and Q2 (CP-22 is agent-internal assembly; no A2A
capability); Q7 (reification plus endpoint closure accepted); Q9(a) (ledger-data route where
appropriate); Q10 (several gates: composition today, backlog); Q11 (invoke-time conditioning
suffices; plan id per perspective is backlog); Q12(a) (the low road carries aggregation shapes);
Q13 (group-scoped children); Q15 (CP-23 and CP-24 defined; the loop is harness-owned); Q16
(membership as an entity attribute); Q6 deferred with A9. The scheduler, alert clustering and
narrative layers are outside the SDK.

**Measured in batch 1 before any ruling to change the SDK** (per §5.0, not implemented yet):
Q3 (A1, the multi-principal door), Q4 (A2, the credential envelope — the determination above says
repeated plumbing around product-specific values; the review after aml's third instance decides),
Q5 (A3, the Similarity query and passage corpus).

**Still open for Dave, in the order they are needed.**

- **Q8 — authorize the one measurement** (A6): does a policy-emptied view's marker reach an
  unentitled principal below full disclosure? One test before mnpi's Gate 1.
- **Q12(b) — the silent pass** (A10): close it with one guard when the first low-road rung (CP-23)
  measures it, or leave it documented?
- **Q14 — kyc's review queue** (Gate 1): the product-scoped `workflow_state_ref` convention and the
  two-record linkage; carry the estate's stored confidence as evidence, or recompute.
- **Q17 — the co-lender's Gate 1:** Route A as the governed spine; amend `require_attestation=false`
  and "unattested → Context Debt"; how `include_federated=false` is demonstrated; whether the reverse
  direction (the peer's agent at our door) is in scope.
- **Q18 — abs's Gate 1:** the granularity-disclosure recast; one role or two; the demonstration
  instant.
- **Q20 — documentation:** is the public package for the policy, temporal and composite clusters
  launch scope, as the replay recipe was? Rubric measures 7 and 8 will put a number on it after
  batch 1.
- **§6 item 1:** an owner rung, or a determination, for local-callable and fixed-MCP-resource
  skills.

---

## 9 · Revised build sequence, and what batch 1 measures

**Batch 1 — the T5 wall products, on the paved road, measuring the three patterns.**
mnpi first (its spec asks for it; it carries all three patterns), then aml and ib reusing its
deployment shape. Before mnpi's Gate 1: the A6 measurement (Q8). Each rung's close report carries the
eight rubric counts; after aml (the third independent implementation of the envelope glue and of
passage retrieval) the abstraction review for A2 and A3 is held, and after ib the review for A1.
Nothing in A1–A7 or A10 is implemented inside the batch.

**The three patterns worth measuring in batch 1, in priority order:**

1. **A2 — the credential-derived policy envelope.** Predicted to repeat on mnpi, aml, ib and kyc;
   the determination is that its values are product policy with a governed home and its plumbing is
   SDK plumbing (a missing role-applicable default and a scalar-only list fold). Highest value
   because the closure, if confirmed, is an arm on an existing artifact with no new seam, and because
   the alternative is every wall product refusing by raise from acquisition code.
2. **A1 — several credentialed principals through one door.** Eight use cases; the shadowing half is
   the one place in this pass where correctness depends on wiring order with no boot-time signal.
3. **A3 — policy-before-similarity over a passage corpus.** Seven use cases; decides whether the
   §7.4(c) headline is demonstrable through the operator plan or only acquisition-side.

**Batch 2 — CP-22 and kyc, in parallel with batch 1's reviews.** CP-22 needs no ruling and no SDK
change and proves the agent-internal boundary quickly on the hw1 product. kyc carries the HITL
composition (P1; Q14 at its Gate 1) and is the fourth instance of the envelope glue, so it waits for
the A2 review's outcome before it copies or declares.

**Batch 3 — abs**, after Q18 at its Gate 1: the granularity ceiling and the first live 341-1.

**Batch 4 — the portfolio and group products, sharing one aggregation shape.** CP-23 first (the
first multi-anchor low-road product; measures A10 and the limit arithmetic once), then large exposure
(reusing the group-scoped exposure producer and the same arithmetic — the second instance), then
CP-24 (the scenario over CP-23's context). The group-scoped producers are authorized at CP-23's
Gate 1.

**Batch 5 — the co-lender**, on Route A, after Q17 at its Gate 1; the first two-tenant admission and
the first live child-bound TTL floor.

Every rung is built to the minimum that drives its supported-unproven rows and records its rubric
counts, and stops at the first bucket-4 or bucket-5 finding (§J). The three-issue cap has headroom
three today (no SDK issue is open); a rubric result of "launch concern" spends one.

---

## 10 · What remains unverified, and where the evidence lives

**Unfinished.** The adversarial verification stage (three refutation lenses on every gap row, an
audit of every "supported" row, a challenge of every deferred row) completed only for the
portfolio-management placeholder before the credit outage ended the run; the seven vault specs carry
analyst classifications with tree citations that the critic spot-checked but no verifier attacked.
The rubric measurement in batch 1 is the verification that matters now: it replaces predicted
friction with counted friction on real rungs.

**Not analyzed** (critic): nine items, each now placed — mnpi's Batch Enrich step (bucket 1), ib's
Reg FD binding (inherited), aml's BSA/AML rules (folded), the capstone's capital-base estate row, the
co-lender's institution-identity estate row, kyc's false-positive pair (estate), the original A2A
variant's D-IMPL-14 drift row (moot after the re-scope), and a source-side ledger time-travel caveat
for aml, large exposure and mnpi (§7). The §D acquire-mechanism hole is §6 item 1.

**Evidence.** `qualification/gate-0-cp15-24/evidence.tar.gz` holds, unedited: the ten capability-map
inventories, the nine analyses and the six augmented analyses, the two verdict files, the synthesis
and the critic, as the agents returned them for revision 1. The CP-23 and CP-24 definitions derive
from `references/cbcib-portfolio-management-CLAUDE.md` (Dave's `cbcib` requirements as supplied on
2026-09-20). The vault specs are canonical for the seven products; the tree at `7356a0f1` is
canonical for the SDK.

---

## Appendix A · Corrections from the completeness critic applied in this document

Thirteen wrong-module or absent symbol citations and one wrong-file test citation are corrected
where the mechanism is named above (`PRODUCT_REQUEST_TOOL` lives in `src/ccf/products/door.py`;
`AcquisitionSeamProtocol` in `src/ccf/products/resolver.py`; `EnvironmentValue` in
`src/ccf/deployment/environment.py`; `CATEGORY_ORDER` in `src/ccf/operators/base.py`;
`SimilaritySelectParametersArtifact` in `src/ccf/controlplane/artifacts.py`; `DeclaredProductGate`
in `src/ccf/products/contract.py`; the content-generation archetype is
`src/ccf/agents/archetypes.py` (`_ContentGenerationComponent`); no symbol named `PolicyBundle`
exists — the pin is `pins.version_for` in the resolver). Fourteen cross-use-case inconsistencies are
resolved by one rule each: the freshness SLA is bucket 1 to declare and bucket 6 to enforce;
materialization posture is uniformly an operations concern; discovery is uniformly bucket 6; the
multi-principal door is a bucket-1 capability plus a bucket-2 friction row; the requested-perspective
limitation applies to aml as to ib and mnpi; several gates per class is bucket 1 by composition plus
one shared §I record; the reader glue half is carried for every rung; the "outlives the process"
half of kyc's review lifecycle is bucket 6; mnpi's zero ranking difference is a reference-index
property (bucket 6), not an estate limitation; the D-IMPL-49 drift is narrower than "never built";
the "entities only for v1" ruling is cited by its heading (D-IMPL-334 ruling table); the PM fan-out
row is multi-anchor low-road aggregation, not the excluded composite fan-out.

## Appendix B · Dave's Gate-0 direction of 2026-09-20, as applied

1. CP-22 re-scoped to agent-internal assembly; A8 withdrawn; no A2A SDK capability (§3, §4.2).
2. Adoption friction is a launch concern, measured by the eight-measure rubric and the four-class
   result; three independent implementations trigger an abstraction review; A1–A7 and A10
   re-evaluated and not implemented (§5.0, §5.1); A2 determined to be repeated SDK plumbing around
   legitimately product-specific values (§5.1).
3. CP-23 and CP-24 defined from the `cbcib` requirements (§4.2); the monitoring loop is
   harness/agent-owned; products are assembled when invoked.
4. Group-scoped children, reification plus endpoint closure, invoke-time conditioning, the
   ledger-data route where appropriate, gates as composition/backlog, low-road aggregation, the
   post-launch items and the estate-limitation rule are preserved (§1).
5. Matrix and decisions updated; revised sequence and the three patterns to measure (§9); no new
   D-IMPL; no implementation started.
