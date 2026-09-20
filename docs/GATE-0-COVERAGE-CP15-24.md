# Gate-0 coverage matrix — CP-15 through CP-24

**Status.** The Gate-0 coverage pass the RELEASE RULING of 2026-09-19 (`docs/DECISIONS.md`)
asked for, delivered on Dave's GO. Read-only against the vault and the tree; no code, no CP-15
build, no decision id spent. Measured against the qualified baseline `2c9d7ba7` (`main` at
`7356a0f1` while the pass ran, 2026-09-19 to 2026-09-20). One capability matrix across every
remaining use case, so that a capability shared by two of them is discovered and designed once,
followed by implementation in batches by capability gap rather than in numerical order.

**The answer in one sentence.** None of the seven vault specs requires a capability the SDK does
not have; every one is buildable today on a supported route. The single bucket-4 item in the pass
is the A2A variant, and it is conditional on one reading of Dave's definition (Q1). What the seven
specs expose instead is a set of *shared* friction and coverage gaps: eight of the ten use cases
need several credentialed principals through one door, eight need a policy envelope derived from
the credential, seven need policy-before-similarity over a passage corpus, and seven need several
declared product gates on one class. Those are the batches.

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
| CP-20 | `syndicated-lending-co-lender` | vault `context-products` | T5 + A2A |
| CP-21 | `large-exposure-rwa-concentration` | vault `context-products` | T5 capstone |
| CP-22 | A2A same-process variant of an already-solved use case | Dave's definition; no vault spec | — |
| CP-23 | Portfolio Management use case 1 | definition pending | — |
| CP-24 | Portfolio Management use case 2 | definition pending | — |

The CP numbers are positional labels for this document. Dave assigns ladder identities when each
is built; the recommended build order (§9) is not numerical.

**The rule applied to every row** (Dave, 2026-09-19, verbatim in `docs/DECISIONS.md`). First ask
*"What SDK capability does this example require that CP-01–14 have not already proven?"*, then
classify into exactly one of six buckets: (1) already supported → existing path, no redesign;
(2) ergonomics/friction only → backlog unless it makes the supported path impractical;
(3) example/data limitation → record and continue, never repair the SDK for it; (4) missing
capability the use case requires → stop, smallest reusable SDK abstraction; (5) incorrect SDK
behavior → fix; (6) nice-to-have → backlog. *"A new example does not earn permission to redesign
an existing SDK mechanism simply because another design would be cleaner."* Both producer routes
are supported (LAUNCH SCOPE): the paved facade, and lower-level governed assembly plus the standard
door. Launch blocker versus backlog is decided by `docs/EXAMPLE-EVALUATION-CRITERIA.md` §C against
the core launch contract in §D; friction is measured per §E.

Two standing rulings are applied uniformly and are not re-litigated in any row: products are
assembled per request, never precomputed, so a spec's *materialization posture* is an operations
concern outside the launch contract; and post-traversal aggregation is served through the low road
(LAUNCH-BAR row `CP14-F-33`), so the absence of an Aggregate, Rank, Evaluate or Federate operator
category is spec vocabulary, not a gap (the operator vocabulary is closed at four categories in
`src/ccf/operators/base.py` (`OperatorCategory`)).

---

## 2 · Evidence standing — three states, kept apart

The pass ran as an orchestrated workflow in two stages; a usage-credit outage interrupted both, so
the evidence carries three states and every claim below names its state.

| State | What it means | Where it applies |
| --- | --- | --- |
| **Verified** | The analyst's classification was attacked by independent verifiers reading the tree (refute-from-three-lenses on gaps, audit on "supported", challenge on "deferred") and survived or was revised | The two portfolio-management placeholder rows only (29 rows: 21 supported-class rows audited, 8 deferred rows challenged) |
| **Analyst-classified** | One analyst per use case read the spec in full, read the SDK modules named, and classified every capability with tree citations; a second pass augmented six of the nine analyses against the three capability clusters the first pass lost | The seven vault specs and the A2A variant (368 rows) |
| **Not analyzed** | Named by the completeness critic as a capability with no row | Nine items, listed in §10 and folded into the matrix where the disposition is not in doubt |

What was done, by count: ten capability-map clusters over the SDK (policy and entitlement;
traversal, similarity and sources; aggregation, composition and expiry; temporal, policy-version
and replay; peering and A2A; agents, skills and harness; request surface and doors; HITL and
audit; the recorded backlog; estate readiness for the seven products) — 210 mechanism rows with
module, symbol, proof and known limitations; nine use-case analyses (397 rows after augmentation);
one synthesis (26 batches, 37 estate limitations, 20 questions); one completeness critic, which
resolved 3,343 path citations, 691 test-node citations (1 wrong file) and 2,830 symbol citations
(13 wrong module or absent) against the tree, found 9 capabilities with no row, 14 cross-use-case
inconsistencies and 5 launch-contract items no rung carries. The critic's corrections are applied
in this document (Appendix A); the raw analyses are preserved unedited in the evidence tarball
(§10).

**How to read a row.** *Supported* means a proven path exists on CP-01–14; *supported-unproven*
means the mechanism exists (unit- or conformance-proven) but no rung has driven the spec's exact
shape — an example obligation, not an SDK gap. Fifty-one rows across the nine analyses are
supported-unproven; the proof batches (§5.3) absorb them.

---

## 3 · The result in one page

**Bucket distribution after augmentation** (rows per use case; PM row reflects the verified
revisions; the "4" column for the A2A variant is conditional on Q1):

| Use case | rows | (1) supported | (2) friction | (3) estate | (4) missing | (5) incorrect | (6) later |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CP-15 kyc | 61 | 41 | 9 | 8 | 0 | 0 | 3 |
| CP-16 abs | 46 | 32 | 7 | 6 | 0 | 0 | 1 |
| CP-17 mnpi | 54 | 33 | 12 | 4 | 0 | 0 | 5 |
| CP-18 ib | 43 | 28 | 9 | 5 | 0 | 0 | 1 |
| CP-19 aml | 40 | 29 | 5 | 5 | 0 | 0 | 1 |
| CP-20 co-lender | 37 | 28 | 6 | 1 | 0 | 0 | 2 |
| CP-21 large exposure | 59 | 32 | 10 | 6 | 0 | 0 | 11 |
| CP-22 A2A variant | 28 | 18 | 5 | 1 | 3 (Q1) | 0 (Q6 may move one) | 1 |
| CP-23/24 PM (placeholders) | 29 | 17 | 5 | 1 | 0 | 0 | 6 |

**Three things the counts say.** No vault spec is blocked on the SDK. The bucket-2 column is where
the work is, and it is *shared*: the same seven or eight gaps recur across the T5 specs. The
bucket-6 column on the capstone is large because the spec composes every primitive below it and
several of those compositions (fan-out, artifact-by-instant, durable audit) are excluded from the
launch contract by standing rulings, not by this pass.

**The one candidate launch blocker.** The A2A variant as Dave phrased it — *"a client agent reaches
its context from a second agent over A2A"* — reads as request/response: the client asks, the
producer answers. The SDK's A2A is a **push** carriage between two fabrics: `PeeringProtocol`
(`src/ccf/peering/protocol.py`) declares `emit` and `receive` only, the skill dispatch drains what
arrived (`src/ccf/skills/dispatch.py` (`_invoke_peering`)), and the LF A2A executor frames an
inbound signed product and replies with a carriage id (`runtime/ccf_runtime/peering/lf_a2a.py`
(`_InboundExecutor`)). Under the push reading every mechanism exists and is proven across two OS
processes (`tests/crossproc/test_peering_exchange.py`, both wire legs). Under the request/response
reading an A2A product door is missing, and D-IMPL-14's own wording ("the task/artifact model …
carrying the typed Context Product as the artifact payload") describes the request/response shape,
so the shipped wire may also be a drift from that ruling. This is Q1, and it decides the only
bucket-4 item.

---

## 4 · The matrix

### 4.1 Overview — Dave's six columns

| Use case | Capability tested (what nothing before it proved) | Existing SDK mechanism that should satisfy it | Genuinely new capability | Likely friction (measured) | Implementable today | Launch blocker vs backlog |
| --- | --- | --- | --- | --- | --- | --- |
| **CP-15 kyc** | A sub-threshold finding kept *inside* the product and handed to the SDK `ReviewQueue` with the served content address as `output_ref` (first product-side HITL composition); per-person resolution confidence as a claim attribute end to end; multiplicative ownership with the revisit cap disclosed; a request default *per entitlement*; evidence-anchored 24 h TTL over a sanctions publish date | Paved road (`open_product` + `open_door`); `src/ccf/hitl/review_queue.py` (`ReviewQueue`); `RelationshipClaim` attributes; cp-04-canonical circuits and s1-01 ownership recursion as Π precedents; `PolicyConstraintResolver` seam; `from_entity_freshness` | none | Second instance of acquisition-seam entitlement glue (~60 lines); readers restated (~150 lines, 6th tree); passage cite/re-hash copied (~70 lines, 2nd); ReviewQueue composition = 4 injected objects + 1 policy artifact + a `LineageEntry` per flagged person + an undefined product-scoped `workflow_state_ref`; three spec gates in one slot; fractional parameters as decimal text | Yes on the paved road; partial for the review-queue convention (Q14) and for the 24 h anchor on a snapshot (illustrative window under D-IMPL-323) | Backlog (9 friction rows); no blocker |
| **CP-16 abs** | Granularity as a governed cost-and-shape lever: an enum parameter with a role-applicable `allowed_set` ceiling that refuses `loan` by name; first class combining an evidence-anchored TTL with a decision-instant parameter (residual 341-1 goes live); loan grain without materializing a 1.3 M-row pool; trigger thresholds anchored by passage re-hash | `ArgumentDomain.members`; `PolicyConstraint` + `ConstraintApplicability.perspective_role`; `decision_instant_parameter`; `resolve_ttl_anchor`; `PassageAnchor`; paved road, low road reserved for loan grain | none | Applicability by role, not principal (2 principals → 2 roles + 1 constraint + ~2 glue functions for the second principal at the door); the spec's "lower and disclose" gate recast to refuse-by-name; request schema and cost note reach no caller (24.7-C-01); date-typed `as_of` as decision instant is an unmeasured serve-time risk; three estate tables duplicate the Control Plane ceiling; six spec operators map to three keys; three readers; two gates, one slot; 24 h TTL vs monthly data | Yes (32 supported + 5 supported-unproven of 46 rows) | Backlog (7); spec gate recast (Q18); no blocker |
| **CP-17 mnpi** | Entitlement as a *formative* constraint sourced from the credential: one address, three credentials, three structurally different products whose bounding sets come from the grant; bitemporal wall state; a supersede-only half-life in a served product; the Reg FD *widening* supersession as admission; the departmental SQLite restricted list read first; no disclosure including the SDK's own marker channel | `open_door` overrides (`token_verifier`, `entitlement_source`, `perspective_resolver`); `ProductEntitlementPolicy` with N grants; `PolicyFilter` formative substitution + GQ-16 endpoint closure (reification); `AcquisitionContext.perspective`; the invalidation register; supersede-only decay; `ComputedEmptyFinding` + disclosure | none; two conditional (Q7: one class varying its traversal vocabulary per principal; Q8: a served policy marker as a breach) | Three principals need 3 override objects and one ordering rule (`open_door` registers a one-principal policy unconditionally; latest-wins shadowing); per-principal sets only at the acquisition seam (2nd rewrite of cp-13's glue); edge vocabulary via reification + 1 containment gate; one `plan_id` with a role branch; requested perspective on HTTP only; a `perspective` argument is accepted and never honored; `known_as_of` as deployment glue; first SQLite source | Partial-to-yes on the paved road | Backlog (12); one candidate ergonomics blocker to rule (the three-principal door, Q3) |
| **CP-18 ib** | Π as a dimension of the product on a *consumer-anchored* subject: a policy-versioned, perspective-selected weight vector pinned in lineage so a ranking replays under the prior version; three orderings from identical signals through one class and one door; wall state inherited from mnpi; banker-local SQLite notes as claims that move a ranking | Opaque `ProductRequest.subject`; `ProjectionPlan.invoke(perspective=)`; the manifest pin (`pins.version_for`) into `policy_bundle_versions` and replay dimension 2; the adopter `policy` section as the only pinned slot; `PerspectiveResolverProtocol`; `PolicyFilter` structural absence; `EnvironmentDocument.sources` | none | 40 bankers under 3 perspectives through one door = 2 typed overrides or a hand-registered 40-grant policy (composition with the door's own registration unproven); weight vector pinnable only inside the policy bundle (66 Decimal strings; cp-07's disk-read projection is the silent counter-pattern); wall exclusion glue, 3rd writing; one permitted set across all mapped classes; 4 invariants, 1 slot; passage retrieval outside the operator; payload nesting ceiling | Partial-to-yes | Backlog (7 bucket-2 candidates; strongest §J case is the envelope glue) |
| **CP-19 aml** | Whitepaper §7.4(c) — four-operator policy-before-similarity on a domain rung as a *served operator-plan fact*; a filing posture in force at a past `as_of`; three perspectives differing in what is assembled; SAR confidentiality read from SQLite before anything runs | `CATEGORY_ORDER`; `SimilaritySelect`, `PolicyFilter`, `TemporalAsOf`; `build_operator_registry` → `TokenOverlapIndex`; `constraints_in_force` effectivity windows; `open_door` overrides; disclosure layer | none; two bucket-2 candidates (a request-bound Similarity query; the credential envelope, 3rd writing) | As mnpi, plus: posture windows derived by the deployment (2 glue functions); one permitted set across four classes; five invariants, one slot; four readers | Yes on the paved road with the lexical index; the vector path is blocked by the estate (72 advisory passages carry no embedding) and no shipped embedder | Backlog; Q5 on the Similarity query; build after mnpi |
| **CP-20 co-lender** | A composite admitting a child produced by a *second deployment of another organization* under a negotiated asymmetric envelope; the peer-declared TTL flooring the composite (first live carrier of residual 341-4); remote-attested vs local-reconstructible provenance kept apart; whether a question-bearing *and* signature-attested pull has a home; the peer's agent as a second credentialed principal | Route A `mcp_product` (the cp-14 chain: `McpProducerRegistration`, `QuestionBoundChildResolver`, `CompositeAdmissionGate`, D-IMPL-340 proofs); Route B peering (`PeeringAdmissionGate` with the consumer-tenant stamp, `DetachedJwsIdentityProvider`, `PeerTrustGrant`, `verify_child_eligibility`, `LfA2AWire`/typed HTTP, `build_children=` hatch); `compose_expiry`; federated TTL vs consumer `MAX_TTL`; `PolicyConstraint` effectivity for competition-law rules | none classified; the nearest candidate is the same question as CP-22 (question + attestation on one route) | Route B is not declarable (no peering section in the deployment config or binder; 89 hand-wired consumer lines on the archived example); a second full producer tree over the peer estate; five SDK-internal rules with no public page; two credentialed principals at one door (~15–25 lines of overrides); `include_federated` needs a second class or a `build_children` wrapper; list-envelope containment is glue; the envelope maps to three SDK identities across two deployments; latency and attestation are *declarations* in the peer's data | Yes on Route A end to end; partial on Route B; the estate is ready (ccf-dataprep 2026-09-19) | No blocker. One route decision and two spec-versus-ruling conflicts before Gate 1 (Q17) |
| **CP-21 large exposure** | A composite whose children are needed for *every member* of a derived group (N anchors × 3 classes) with the group moved by `connection_basis`; regime as a policy envelope at `as_of`; an object-valued `proposal` computed with and without; worst-of inherited debt with tolerance fail-closed; three perspectives; four stores including the SQLite limit workbook; examiner replay | `ChildRequirement` (one requirement per class, one subject per question); `CompositeAdmissionGate`; `compose_expiry`; `compose_debt_factors`; the cp-14 chain; regime versions as ledger data cut by `TemporalAsOf` or as `PolicyConstraint` artifacts; one closed object level on `SkillArgumentProperty`; low road + standard door for a group-scoped exposure producer | none; conditional: per-member fan-out of one class is bucket 4 only if Q13 rules §D step 6 literal (excluded pre-tag by D-IMPL-343 B-20) | The supported path needs 1–2 *new* group-scoped producer trees (the frozen cp-05 door pins its instant and threads no families); two instants and only `asked_at` reaches constraints; three principals via overrides; one gate for three; four readers; regime-as-data does not move `policy_version` | Partial — buildable as a composite over group-scoped children; a composite behind a door is unproven | Not a blocker; Q13 decides as-written vs re-scoped |
| **CP-22 A2A variant** | Whether a client agent can *ask* for a governed product over A2A and receive it: the transport-axis twin of hw1 (same content address over MCP and A2A for one question and instant) with the producing agent, its fabric and its endpoint in one process. Base product: `examples/hw1-companies-over-revenue` (the only product with an executing two-transport identity proof and a three-harness proof) | Push peering end to end (`LfA2AWire` emit/receive/routes, `build_agent_card`, signing, admission, trust grant, skill dispatch, harness adapters, `mount_product_source`; the LF A2A leg of `tests/crossproc`); the client ask over MCP (client schemes `inprocess` and `mcp+stdio`; `runtime/ccf_runtime/mcp/product_door.py`) | **An A2A request/response door with requester identity at the producer — bucket 4 only under the request/response reading (Q1); none under push.** Plus a candidate bucket-5 drift row: D-IMPL-14's task/artifact wording versus the shipped raw-part push | Producer hosting is hand-composed (7 + 4 + 3 constructor values, ~25 lines of socket/uvicorn glue); consumer admission hand-composed (8 args, trust policy completed in code); no schema for endpoint, card or ceiling; four SDK-internal rules (emit refuses inside a running loop; receive drains; arguments are recorded, never transmitted; the product must claim the *consumer's* tenant); producer replay on emit is silent; record identity differs by construction across the two routes; a CCF-free client is unattainable on the push wire; the Claude Agent SDK has no A2A client | Partial — yes under push with no SDK change, but the identity proof then needs one `tenant_id` on both deployments and the same question and instant on both legs; no under request/response | **Launch-blocker candidate pending Q1**; producer replay on emit is bucket 2 or 5 (Q6) |
| **CP-23/24 PM** | Definition pending. Hypothesized: one governed product over *many* anchors (a book as subject; no rung has put more than one anchor through one product), portfolio-grain aggregation against limits and a capital base, worst-factor debt over N members, a what-if proposal, per-member invalidation, role-conditioned views, a periodic sweep as a replay fact, a limit-breach exception path, a remote member from a second deployment | Low road (cp-05 shape; the builder accepts composite children); `compose_debt_factors`; `run_gates(touched_entities)`; `PolicyConstraint`; `invoke(perspective=)`; `build_egress_server`; the HTTP route; `ExceptionEscalation`; the cp-14 chain for a remote member | none provided the low road is the route; conditional on the definitions: fan-out (excluded), a limit-evaluate primitive (domain values, out of scope), a grant-level book scope (CP14-F-29 backlog), a trigger-activation record (declared, unmechanized — only if ruled inside the contract) | Low road cost (cp-05: 2,382 lines over 5 files vs cp-04-canonical: 1,102); array and object parameters carry no domain; array *order is identity*; limit arithmetic has no SDK home (would be the 3rd instance); capital base and limits in three stores under different names; `touched_entities` must enumerate every member or the invalidation gate passes silently | Yes for the product itself; the sweep loop is harness-owned by ruling | No blocker; Q15 (definitions), Q16 (edge-grain invalidation) |

### 4.2 Per-row notes the overview cannot carry

**CP-15 kyc.** The headline is a proof, not a mechanism: `ReviewQueue.submit_for_review` and the
transport, two delivery surfaces and the replay landing are unit-, workflow- and cross-process
proven, but no active example composes a HITL primitive with a *product* (the only end-to-end
drives are the archived workflow examples, deselected under D-IMPL-265). The one convention to rule
is what a product-scoped review passes as `PendingHitlEvent.workflow_state_ref` (recommended: the
served record's replay reference) and that the product's own record carries `NO_HITL_ACTIONS` by
construction, the human verdict landing on a second record linked by the content hash (Q14). Rows
added by augmentation and worth Dave's eye: a same-day sanctions addition is honored on re-serve by
the invalidation gate (supported); an ownership *change* reaches the register only when the reified
ownership node is an entity claim, because relationship supersession never calls the sink
(`src/ccf/graph/_writer.py` (`upsert_relationship`)) — the same silent-pass shape Batch A8 raises;
the spec's second prerequisite, `counterparty-reference-snapshot`, has no canonical producer to
require (cp-01 is a frozen specimen), so the rung reads the reference rows itself. Estate: the
`controls` predicate carries no assertions; `identifiedAs`/`sameAs` exist only as 74 reified
`IdentityResolution` nodes; the §F false-positive pair is carried as `owl:differentFrom` (74).

**CP-16 abs.** The spec's "if policy lowered the granularity, say so" cannot be authored as
written: the constraint layer refuses an out-of-bound value by name with the bound attached and
never narrows it (D-IMPL-251); the honest recast is "a request above the role's ceiling is refused
`not-in-allowed-set` carrying the bound; a served product states its effective granularity" (Q18).
Loan grain: no SDK row or fan-out ceiling exists (only `traversal-depth`), and the engine
materializes the full as-of view, so `loan` must aggregate and sample in acquisition before
envelopes are emitted, or read the pre-aggregated cohort rows — the fabric-side cost curve has never
been measured on any rung (largest shipped: cp-07 at 240 interactions). Residual 341-1 becomes live
for the first time: the anchor reduces at the decision instant while the reference scorer reduces
at the view instant, so acquisition must be bounded at the decision instant — a rule stated nowhere
public.

**CP-17 mnpi.** Three of the spec's mechanisms are realized *differently* from its wording and must
be disclosed rather than repaired: "the edge is not in the traversal's vocabulary" is realized by
reifying MNPI-bearing engagements as classified entities excluded by `PolicyFilter` before the walk
(endpoint closure guarantees no edge to them survives); `projection_plan_id` per perspective is
realized as one `plan_id` with a role branch, answered from replay dimensions 5 and 4; and
"perspective requested but refused, not downgraded" is exercisable over HTTP only (both MCP doors
call the resolver with no requested role). The Batch Enrich step (§D step 6) had no row; it is
bucket 1 on the cp-13-canonical precedent. The §F measurement "restricted documents would have
altered similarity ranking" is structurally zero under the reference per-candidate index (a lexical
Jaccard against a fixed floor, no top-k) — a property of the SDK's reference substrate, not of the
data, so it is recorded as backlog (a corpus-relative reference index or a Π-side cutoff), not as an
estate limitation. Estate: the per-principal edge types the estate's projection plans name match
none of the 181 predicates in `fibo-v2`; the relationships exist as Postgres rows.

**CP-18 ib.** The only pinned adopter slot is the `policy` section of the deployment config, so the
66-row weight table must live inside the policy bundle and Π must read it through a late-bound
Control Plane closure; that is supported and unproven by any rung, and it is the *correct* route —
cp-07 reads its projection weights from disk, which never reaches `policy_version`. Reg FD had no ib
row; it is inherited from mnpi's versioned policy binding. Build after mnpi and compose its wall
state as a governed child; reading mnpi's tables raw would be §J's "reconstruction of child-owned
data".

**CP-19 aml.** The spec's per-alert similarity query has no home: `SimilaritySelectParameters.query`
is an artifact literal with no request-bound arm, so the SDK operator can rank against a class-level
typology vocabulary while the per-alert match rides the `matchesTypology` traversal, or the rung
ranks acquisition-side and leaves the headline undemonstrated (Q5). BSA/AML program rules fold into
the permitted-disposition row. Estate: transactions end 2026-08-24 against a 1-hour half-life, so
either an illustrative half-life under D-IMPL-323 or a pinned historical `as_of` (the spec's own
examiner parameter) — both honest, Dave's choice.

**CP-20 co-lender.** The route decision drives everything. Route A (`mcp_product`) is the qualified
cp-14 chain and carries a *question* but no signature; Route B (peering) carries a signature, per-peer
trust and producer-attested eligibility but is push-only with no question, stamps the *consumer's*
tenant on the product, and is not declarable on the paved config. Two spec statements contradict
standing rulings and must be amended rather than built around: `require_attestation=false` is
unexpressible (D-IMPL-16 verifies every inbound product, no fast path), and "an unattested remote
claim is recorded as Context Debt rather than admitted" contradicts D-IMPL-336 F1 (a refused child
refuses the composite even in an optional slot; only an honest no-producer absence is priced as
completeness) — the SDK's outcome for the NULL-attestation declaration is a governed refusal, which
`docs/EXAMPLE-EVALUATION-CRITERIA.md` §A names a success. `max_federation_latency` exists as one
environment-level deadline on the MCP bridge, not as a per-request or per-peer parameter; the
peer's `declared_latency_ms` of 7200 is a declaration the projection compares, not a hang the SDK
times out. The spec's `federation_envelope_id` and per-claim "remote-attested" marking have no slot on
`ContextProductContract` or `ProductLineage` by ruling (D-IMPL-58 reading (d)); the separation lives
on `AdmissionRecord` and the composite's `ChildResolution` row. Estate, as ccf-dataprep states it
(vault `contrib/ccf-dataprep/co-lender-peer-estate-as-measured`, 2026-09-19): one peer fabric holds
both counterparties (Fluree `:8091` ledger `bofa/syndicate`; Postgres database `bofa_syndicated`,
schema `colender`; Mongo `bofa_syndicated` empty by design), so the multi-peer request collapses to
one child whose question carries the list; RSSD identity and Call Reports exist for 16 of 45
members; `own_position` covers 5 of 12 syndicated facilities; no 8-K announcement dates. Credentials
live only in Dave's shell exports and need an interactive shell; `.env.example` documents a peer
that does not exist.

**CP-21 large exposure.** `requires` admits one requirement per class with one subject per
question, so N covenant and M collateral questions of two classes are not expressible under one
composite; the supported path is group-scoped child classes (cp-05 already answers a family from one
anchor; cp-06-canonical's borrower scope is an array). That means one or two new group-scoped
producer trees on the low road before the capstone can be declared — example work, authorized or
not by Q13. Regime versions and limit envelopes exist as ledger nodes with effective dates and as
Postgres rows; only a registered `PolicyConstraint` moves `policy_version`, so the examiner's
"policy in force at `as_of`" is either the ledger-data route or a deployment
`PolicyConstraintResolver` (Q9). Estate rows added: FFIEC 101 was never fetched and no FR Y-9C
holding-company base exists (every RWA figure is standardized bank-level, a named validator GAP);
no connected-group registry (groups are derived components; `group_id` is spec vocabulary the estate
cannot key); economic-dependency author and date are node literals, ambiguous for a node with two
edges; both proposal rows are hypothetical and suffice for the breach and fits-after-mitigation cases.

**CP-22 A2A variant.** Nine sub-questions, of which one decides the bucket (Q1) and the rest fix the
shape (Q2): what "in the same process" means (producer agent, fabric and endpoint in one process
with the client elsewhere is proven; both agents in one loop is unproven — `emit` refuses inside a
running loop, `emit_async` is the path); whether the client must stay CCF-free (it cannot on the
push wire: a peering consumer is a fabric by D-IMPL-59); which harness legs (ADK has a native A2A
client; LangGraph can wrap one as a tool; the Claude Agent SDK has none and can only consume a
peered product re-exposed over the MCP door); and what identity is asserted (content-address
equality holds only with one `tenant_id` on both deployments, because the tenant is inside the
canonical bytes and the peering gate refuses a product that does not claim the consumer's tenant;
record identity differs by construction). Documentation drift to fix regardless of Q1:
`public/how-to/run-agents-cross-process.md` presents the archived typed-HTTP example as A2A and as
running in CI.

**CP-23/24 PM.** The verified analysis corrected one false bucket-6: the HITL exception path is an
existing, CI-invariant-covered capability, so whether a PM case *exercises* it is a scope call, not
a gap. Twelve "supported" rows were revised to supported-unproven because no rung has put more than
one anchor through one product. Two determinations are owed before either case is defined: whether
a scheduled sweep and a HITL exception path are inside the initial release contract, and the subject
of each case (Q15). Edge-modeled membership (coverage assignment, sponsor ownership) stays eligible
after the edge is superseded, silently — the "entities only for v1" ruling (D-IMPL-334 ruling
table) — so a definition should model membership as an entity attribute unless Q16 lifts the limb.

---

## 5 · Batches by shared capability gap

Ordered as Dave asked: shared-by-most and launch-relevant first, never numerically. A gap shared by
two use cases is designed once. Every batch states the smallest reusable abstraction as a
*capability*, its §C launch-test answers, and the records that already name it.

### 5.1 Candidates for an SDK change — each needs a ruling before any example builds around it

**A1 · Multi-principal standard door** — shared by 8 (mnpi, aml, ib, abs, kyc, large exposure,
co-lender, PM). N differently-credentialed principals reach one class through one standard door,
each entitled to its own role and disclosure posture, role derived from the verified grant — without
`open_door` (`runtime/ccf_runtime/mcp/product_door.py`) unconditionally registering a one-principal
entitlement policy that silently shadows (latest-wins) a deployment's multi-principal policy, and
declarable rather than hand-wired as three typed overrides. *Smallest abstraction:* `open_door`
refuses to register when a policy already stands under the tenant key, or derives its grant from
it; a `principals:` block under the entitlement policy in the single-file config (the schema
already expresses N grants). *§C:* step 1 YES (the override trio carries N credentials today;
`build_egress_server` is the multi-principal low-road door; the HTTP route entitles per verified
grant); step 2 candidate YES — the shadowing surfaces only at serve as a shell, and every T5 rung
would meet it. Records: D-IMPL-67, D-IMPL-108, D-IMPL-243, D-IMPL-254, D-IMPL-343 design P11'.
**Q3.**

**A2 · Credential-derived per-principal envelope reaching the operator plan and the effective
request** — shared by 8. A permitted set (party, document or edge classes), a request default
("per entitlement", "per perspective", "per entitlement and domicile", the PM's own book) or a
per-perspective bound sourced from the verified grant rather than a caller-stated parameter. Today
`RequestBoundParameter` reads only the effective request and `ProductRequestContract.defaults` is
one literal per parameter; the ruled home is the acquisition seam (`AcquisitionContext.perspective`),
which cp-13-canonical wrote as one dataclass, three functions and two exception classes — mnpi would
be the second writing, aml, ib and kyc the third to fifth, which is §J's stop condition. *Smallest
abstraction:* the seam that already exists — a deployment `PolicyConstraintResolver` injected at
`open_product(constraint_resolver=)` receives the verified perspective, tenant, intent and contract
and returns an `EffectiveRequest` with authority `policy` and the entitlement policy as provenance,
landing on replay dimension 2; a reference implementation would make it the supported path rather
than a Protocol adopters rediscover. *§C:* step 1 YES (three supported paths keep "nothing
inadmissible is ever materialized" honest); step 2 candidate — measured glue at the third instance.
Records: D-IMPL-343 R-4, D-IMPL-253 Q8, D-IMPL-295, CP14-F-29. **Q4.**

**A3 · Policy-before-similarity over a passage corpus as a served operator-plan fact, with a
request-bound query and a pinned index** — shared by 7. The SDK Similarity operator ranks graph
*entities* from a `TokenOverlapIndex` over entity attributes with a class-level literal query; no
vector substrate is wired by the deployment builder and no embedder ships (drift from D-IMPL-07's
"two reference adapters"); per-match scores are dropped. Every T4/T5 spec retrieves passages inside a
policy-permitted set, and cp-13-canonical's acquisition-side retrieval (no index or model pinned,
Similarity absent from the plan) would be copied a third time. *Smallest abstraction, three
separable pieces:* a `RequestBoundParameter` arm on `SimilaritySelectParametersArtifact.query`
(the same mechanism `PolicyFilterParametersArtifact.permitted_classifications` already has); a
passage-corpus source for `SimilaritySelect` (passages ingested as classified entities with a text
attribute); per-match score on the operator's output. *§C:* step 1 YES (policy-before-similarity is
structural in `CATEGORY_ORDER` and candidate containment is conformance-proven); step 2 candidate.
Records: D-IMPL-292, D-IMPL-295, D-IMPL-07, D-IMPL-03, CP13C-F-01, INV-CH7-26/27. **Q5.**

**A4 · Policy and evidence at the decision instant when `as_of` ≠ `asked_at`** — shared by 7.
(a) The constraint and tolerance envelope effective at the *class's decision instant*:
`constraints_in_force` evaluates at `request.asked_at` by ruling (D-IMPL-253 Q6) and the registry
has no `resolve_at` for any artifact class but `PolicyConstraint`; (b) a date-typed `as_of` named as
`decision_instant_parameter` parses to a naive datetime with no boot refusal; (c) an evidence-anchored
TTL combined with a decision-instant parameter (residual 341-1) goes live for the first time on abs.
*Smallest abstraction:* (a) is the ruled seam again — a deployment `PolicyConstraintResolver` may
read `as_of` from the request and select the window — or, if ruled required, one clause letting
`constraints_in_force` take the decision instant; (b) is a boot-time type refusal; (c) is a stated
acquisition-bounding rule. *§C:* step 1 YES (the ledger-data route is example-proven on cp-08 and
cp-11 and the two-instant rule is ruled, D-IMPL-308); step 2 NO for (a), candidate for (b).
Records: D-IMPL-253 Q6, D-IMPL-308, CP14-F-29/F-38, LAUNCH-BAR residuals 341-1/341-2. **Q9.**

**A5 · Several declared product gates per class, each with its own identity and version lane** —
shared by 7. `ProductClassDeclaration.declared_product_gate` holds one gate and
`ProductGateProtocol` is one callable, so a spec's three to five product-level invariants fold into
one composed predicate whose refusal names the bundle and carries the invariant only in a detail
string; the no-disclosure predicate is rewritten per example (cp-01, cp-02, cp-11, then mnpi, kyc,
aml, ib). *Smallest abstraction:* an additive `declared_product_gates` roster beside the singular
field, run in declaration order, with `ProductInvariantRefusal` naming the gate that fired. *§C:*
step 1 YES (cp-08 composes two filters under one gate); step 2 NO as measured — the cost is a
detail string. Records: D-IMPL-282 R-11, D-IMPL-224, cp-08's composed gate. **Q10.**

**A6 · A policy-emptied view served with a marker — a measurement before any build** — shared by 6.
When `policy.principal-subgraph` empties a principal's entire view, the SDK serves a product whose
`ComputedEmptyFinding.operators_returned_empty` names the policy operator (correct for its purpose,
D-IMPL-242 amendment 1). No test exists either way for what an *unentitled* principal receives below
full disclosure. If the marker leaks it is bucket 5 and the smallest fix is the disclosure layer
suppressing policy-operator keys below full disclosure; if a deployment gate converting it to the
canonical unauthorized/nonexistent shell is the intended posture, it is bucket 1 and every wall rung
writes that gate. One test in `tests/products/test_empty_operator_halves.py` settles it. **Q8.**

**A7 · Per-perspective projection-plan selection and pinned Π parameters (the D-IMPL-49 drift)** —
shared by 6. D-IMPL-49 ruled the selection signature (perspective, product class, selection
parameters); the shipped `ProjectionPlanFactoryProtocol.__call__` receives the requirements and the
request only, so the perspective reaches Π at `invoke`, one `plan_id` per class with a role branch is
the only shape, and the estates' plan-per-perspective tables cannot become distinct plan ids in
replay dimension 5. `AgentDefinition.selection_params` exists; the drift is the missing perspective
argument on the factory, not an unbuilt field. *Smallest abstraction:* none for launch (replay
re-feeds the recorded perspective); if ruled bucket 5, add `perspective` to the factory signature.
**Q11.**

**A8 · A2A request/response door** — the pass's only bucket 4, conditional on **Q1**. Shared by the
A2A variant, the co-lender's Federate step (question + attestation on one route) and possibly a PM
consumer. *Smallest abstraction:* one `a2a-sdk` executor mounted beside `LfA2AWire.routes()` that
accepts the hw1 three-field question as one raw part and answers through the *existing* chain
(`verified_grant` → `govern_entitlement` → `door_question`/`door_answer`), signs the outcome with
the producer's identity, and — because this wire carries no bearer token — establishes the requester
from a signed request under the peer's trust grant or the mTLS workload identity D-IMPL-15 names;
consumer side, a request verb or sibling Protocol so both shipped transports stay conforming, a
`peering_product` skill type mirroring `mcp_product`, and a peer registration artifact. The tenant
contract must be ruled first: peering stamps the consumer's tenant, `mcp_product` the producer's
(D-IMPL-340 §9, left open). *§C:* step 1 YES for the SDK contract (§D names peering as an
acquisition mechanism and push meets it; remote producer boundaries are proven over MCP) — so this
is bucket 4 *for the use case*, and the RELEASE RULING's alternative exit is an explicit approved
determination that asking over A2A is outside the initial release contract. Records: D-IMPL-14
(whose task/artifact wording favors the request/response reading), D-IMPL-59, D-IMPL-127 (HW-2),
D-IMPL-133, D-IMPL-340 §1 and §9.

**A9 · Producer-side replay on the peering emit path** — shared by 3 (A2A variant, co-lender, PM
remote member). `PeeringProtocol.emit` and `DetachedJwsIdentityProvider.sign` take a raw contract;
nothing on emit requires `serve()`; no replay reference crosses in `SignedContextProduct`;
`ChildResolution.child_replay_ref` is `None` on the peered leg; the archived producer emits before
it serves. *Smallest abstraction:* emit accepts a `ServedProduct` or refuses an unrecorded contract
by name (the D-IMPL-260 P-A gate the MCP door has), and the producer ref rides the existing
protected-header assertions into the consumer's typed slot. *§C:* step 1 YES; step 2 candidate YES
— the omission never fails. Whether CLAUDE.md §11's "replay-ready by construction" binds the emit
path (bucket 5) or this is ergonomics (bucket 2) is **Q6**.

**A10 · Low-road obligations that pass silently** — shared by 4 (large exposure's group-scoped
exposure producer, abs at loan grain, both PM cases, co-lender fan-in). `run_gates(touched_entities=None)`
passes with no signal when a low-road builder never threaded the set, so dependency invalidation is
disabled invisibly; the pre-acquisition refusal on the low road is raised, unrecorded (LAUNCH-BAR
residual 304). *Smallest abstraction:* no new seam by ruling; one guard refusing by name when a
low-road builder omits `touched_entities`, if Dave wants the silent pass closed. **Q12(b).**

### 5.2 Backlog by existing ruling (§I records; no ruling needed to proceed)

| | Gap | Shared by | Supported path today | Record |
| --- | --- | --- | --- | --- |
| B1 | Element-wise containment of a set-valued request parameter by a role-applicable `allowed_set` (`_refuse_against` folds scalar membership only) | 7 | a seam intersection per deployment; the peer enforces its own envelope on the co-lender route | D-IMPL-253 Q4; PM adjacent: array order is identity, no array domain shape |
| B2 | Requesting a perspective over MCP, and the `perspective` argument shadow (accepted, never honored; only `intent` has a boot refusal) | 5 | HTTP `?role=`; MCP derives the role from the grant | D-IMPL-260 P-D, D-IMPL-264 D-01 |
| B3 | Declared-but-unread Control Plane values: `HalfLifeEntry.supersession_event` is a required label no mechanism reads; `FreshnessSLA.max_age_seconds_by_signal` is judged only at bind time | 7 | declare as documentation; "event-driven" is `decay: supersede-only` | D-GATE-cp-08 ("configuration nobody reads is documentation, not control"), D-IMPL-331/332/333, D-IMPL-106 |
| B4 | A2A deployment declaration: endpoint, card, ceiling and trust as deployment documents with an `open_door`-style facade (0 references to peering in `src/ccf/deployment`) | 3 | driver code and the test fixture | D-IMPL-136/137, D-IMPL-141, 24.7-C-01 |
| B5 | Adopter-facing public pages for the policy, temporal/invalidation/replay and composite clusters (zero public pages measured for entitlement, disclosure levels, `PolicyConstraint`, `RequestBoundParameter`, operator order, the gate slot, supersede-only, relative defaults, the decision instant, `ReplayBinding`, the invalidation register, `open_door`, `build_egress_server`); the tutorial and two how-tos literal-include retired examples | all | source docstrings and `docs/DECISIONS.md` | LAUNCH-BAR "replay recipe" row is the model. **Q20** asks whether this is launch scope |
| B6 | Hand-rolled per-store readers (SPARQL over httpx, psycopg, pymongo, and now sqlite3 for the departmental store) restated per tree; the seven rungs would be the sixth to thirteenth | all | `AcquireProtocol` / `AcquisitionContext.sources` by env-var name | D-IMPL-277 OPEN, D-IMPL-282 R-09 (discoverability, no new Protocol) |
| B7 | Request-surface wire facts every remaining spec meets: fractional parameters as canonical decimal text; an object parameter has crossed no shipped door and a nested fraction has no exact wire form; argument names restated as string constants are unheld against the contract; `policy_overrides` unreachable through either door; the technical capability re-read from YAML | all | proven per item at unit or wire level | D-IMPL-302, D-IMPL-103, CP04C-F-03, CP14-F-21 |

### 5.3 Proof batches — no SDK change; an example must simply drive it

| | What no rung has proven | Carried by |
| --- | --- | --- |
| P1 | A HITL primitive composed with a Context Product: `ReviewQueue` with the served content address as `output_ref`; `ExceptionEscalation` on a computed breach; the human action on replay dimension 2 | kyc (headline), aml, mnpi, large exposure, PM |
| P2 | Supersession compositions: a *widening* supersession as admission (superseding claim on the same `entity_uri` with a world-time `valid_from`); a principal-scoped wall crossing invalidating only products that touched it; per-member invalidation of a multi-anchor product through the real writer → register → gate path | mnpi, ib, abs, large exposure, PM |
| P3 | Composite and cross-deployment proofs: a composite served through the standard MCP door or HTTP route (cp-14 serves in-process); a child arriving over a wire flooring the composite's expiry (residual 341-4); a two-tenant, two-credential `mcp_product` admission; the first shipped optional requirement priced at completeness-when-absent; the first registered `ccf.policy-constraint` from estate rows; the first non-default disclosure posture on a grant | co-lender, large exposure, abs, aml, kyc, PM |
| P4 | A2A variant proofs under either reading: adapter seams exercised with a peering-typed skill under three harnesses; content-address identity across the MCP tool door and LF A2A for one question and instant (the two-transport parity instrument extended by one leg); the single-process topology | A2A variant, co-lender |
| P5 | Monitoring/sweep activation as a replay fact: the loop is harness-owned by ruling; the `MonitoringSurveillanceAgent` archetype's trigger-activation-record obligation is declared and referenced nowhere outside the archetype module — bucket 4 only if Dave rules it inside the initial release contract | PM, aml (periodic sweep), ib |
| P6 | The fifty-one supported-unproven rows: the first `allowed_set` + `perspective_role` constraint (abs); a request-bound permitted set on a T5 rung; passage similarity through the SDK operator; the first departmental-SQLite source; one-address-three-products; three-perspective doors; a policy version pinned through the bundle (ib) | every rung |

### 5.4 Exclusions and the repeated-glue register

**Excluded from launch by standing ruling** (bucket 6, recorded so the partition is complete):
fan-out under one composite (N children of one class, concurrent dispatch, a per-request federation
deadline — D-IMPL-343 B-20; **Q13** asks whether the capstone's §D step 6 forces the question);
discovery of a class's request surface before asking (`render_request_input_schema` has no runtime
consumer; the MCP tool advertises the SDK's fixed eight argument names — D-IMPL-264 amendment 1
F-5); examiner-facing re-execution over an Experience surface and a durable audit plane (the
`AuditLog` is a concrete in-memory class with no Protocol seam; residuals 341-2/341-3 carried);
Control Plane artifact versions selected by a past instant; an assertion-time request axis
(`known_as_of` is deployment glue, as cp-08 wrote it); relationship-grain invalidation (**Q16**).

**Repeated glue, by family and instance count** (`docs/EXAMPLE-EVALUATION-CRITERIA.md` §H: three
instances is the case for an abstraction; §J: the third example writing it stops and raises):
acquisition-seam entitlement glue — cp-13-canonical today, mnpi second, aml/ib/kyc third to fifth
(→ A2); passage retrieval plus cite/re-hash/anchor — cp-13-canonical today, owed by six (→ A3);
the no-disclosure/containment predicate — cp-01, cp-02, cp-11 today, owed by four (→ A5, A6);
per-store readers — five trees measured, owed by seven (→ B6, ruled); the replay environment —
~40 lines per producer plus one private reach, ruled recipe-not-seam (CP06C-F-01); circuit
enumeration and multiplicative ownership — cp-04-canonical and s1-01 today, kyc second; limit and
headroom arithmetic — cp-05 today, large exposure second, a PM case third. Two families are already
at the third instance before any remaining rung is built.

---

## 6 · Coverage holes in the 24 — launch-contract items no rung carries

The critic asked which `docs/EXAMPLE-EVALUATION-CRITERIA.md` §D items are exercised by neither
CP-01–14 nor any remaining use case as analyzed. Four, and they are Dave's to close or to
determine out:

1. **"acquire products through … local callables, fixed MCP resources"** — the local-callable and
   fixed-MCP-resource skill legs are exercised by no active example and no remaining use case; the
   skill-type tokens occur only in the banking test fixtures and the archived examples. The rows
   name `mcp_product` and peering only.
2. **"preserve product identity … whatever transport carried them" across A2A** — proven in-process
   and over the MCP door, and across three harnesses through one MCP door; across a two-tenant
   peering it is unattainable by construction (tenant inside the canonical bytes), so the item as
   worded is exercisable only under a one-tenant precondition neither the launch bar nor this
   matrix had stated until now.
3. **The composite floor bound by a child arriving over a wire** (residual 341-4) — carried only by
   the unbuilt co-lender and PM rows.
4. **An optional requirement priced at completeness-when-absent** — unit-proven only; among the
   remaining use cases only the capstone would declare one (its two prerequisites without producers).

---

## 7 · Estate limitations — recorded, disclosed where the reader meets them, never repaired in the SDK

Every figure below is from the ladder survey (2026-08-28), the store catalog (2026-08-31), the
read-only census of 2026-09-19, or ccf-dataprep's instruments; dates are cited because the estate is
live. Three of the seven products (kyc, abs, mnpi) still have no manifest in ccf-dataprep's
`validators/spec_coverage.py`, so their store assignment is what the spec says plus this pass's
census; aml (16 PASS), co-lender (16 PASS with the peer configured), ib (12/5/1 GAP) and large
exposure (12/4/1 GAP) are probed.

- **Snapshot versus fast half-lives, every product.** Sanctions ~1 day (kyc), transactions ~1 hour
  (aml; newest value date 2026-08-24), positions ~1 hour and the restricted list ~1 day (mnpi),
  spread ~1 day (ib), exposure ~4 hours (large exposure; balances 324–396 hours old, the CP14-F-36
  shape), servicer data monthly against a 24 h TTL (abs): each needs an illustrative calibration
  disclosed at every site under D-IMPL-323's four conditions, or a pinned historical `as_of` where
  the spec itself makes `as_of` a parameter. Never by moving `asked_at` silently.
- **Passages without embeddings.** 14,289 of 37,865 passages (37.7%) carry no usable vector; the 72
  FinCEN advisory passages (aml) carry neither embedding nor sha256; the 12 syndicate agreement
  passages carry no embedding. The 476 regime and methodology passages (large exposure) all carry
  vectors. cp-13-canonical's `not_evaluable` disclosure is the supported reading.
- **Vocabulary divergence from the specs.** `controls` carries no assertions (kyc, mnpi);
  `collateralizes`/`subordinateTo`/`triggeredBy` as spelled do not exist (abs uses the FIBO terms;
  `TriggerEvent` and `TrancheType` sit in Provisional FIBO modules); `identifiedAs`/`sameAs` are 74
  reified resolution nodes (kyc); `beneficialOwnerOf`/`relatedAlert` are the FIBO IRI and a Postgres
  link table (aml); the mnpi per-principal edge types match none of the 181 predicates;
  `participatesIn` is deliberately not minted — the share lives on 97 reified participation nodes
  (co-lender); residency constraints name countries while parties carry ISO3 (aml).
- **As-of over the Fluree HTTP path silently ignores the ledger `t`** (ccf-dataprep known-issues
  §51); only cp-08's SPARQL `FROM <ledger@t:N>` form is honored, and it is deployment SPARQL, not SDK
  mechanism — the fabric's own snapshot pin is what replay resolves (D-IMPL-88). Every "wall state at
  `as_of`", "posture at `as_of`", "regime at `as_of`" and "trigger definition at the ledger point"
  row derives its answer from effective-date literals. Date literals must stay untyped (§59); loaders
  are never re-run (§13.3, positional identity).
- **Thin positive classes, honest not defective (§J).** One engineered trigger amendment and one
  vintage cell with two deals (abs); 18 MNPI-bearing interactions and one Reg FD event (mnpi); 24
  typology matches and one near-match (aml); one insider designation exercised on the absolute cap
  only, 4 economic-dependency edges (large exposure); 4 restricted-list rows all still active (ib,
  mnpi); every sanctions match synthetic by construction (kyc).
- **Missing halves the specs assume.** No banker-to-perspective table (ib; the desk mapping is a
  judgement call in ccf-dataprep's ranker); wall crossings keyed to the mnpi principals, not to
  bankers (ib); the S-1 half of the registration pipeline (ib, named GAP); FFIEC 101 and FR Y-9C
  (large exposure, named GAP); no connected-group registry (large exposure); blackout windows have no
  type or predicate (mnpi); RSSD and Call Reports for 16 of 45 syndicate members, own position for 5
  of 12 facilities, no amendment announcement dates (co-lender); `counterparty-reference-snapshot`
  has no canonical producer to require (kyc).
- **Frozen specimens are not usable as children.** The frozen cp-05 door pins its instant and
  threads no families (CP05D-F-01), so the capstone's exposure child is a new group-scoped producer;
  cp-01 fails construction on the current SDK.
- **The peer estate** (ccf-dataprep states, 2026-09-19): two counterparties on one fabric; three
  engineered conditions are declarations in data (band-only disclosure, `declared_latency_ms` 7200
  against a 10,800 s TTL, a NULL attestation); MongoDB empty by design; isolation is software-only
  (shared host, Postgres shares the port); the isolation validator collects zero tests under pytest
  and must be run as a script.

---

## 8 · Questions for Dave

Only decisions the matrix cannot settle. Grouped by what each decides.

**Decides a bucket**

- **Q1 — the A2A variant's reading (the only bucket 4).** Does "a client agent reaches its context
  from a second agent over A2A" mean the client *asks* over A2A and receives the product
  (request/response, the twin of hw1 and of D-IMPL-127's HW-2), or the SDK's push model (the producer
  emits a signed product it chose; the client's fabric admits and consumes)? The tree supports only
  push. Request/response: fund the smallest A2A door (A8) or record an explicit approved
  determination that asking over A2A is outside the initial release contract and re-scope the
  variant to push. D-IMPL-14's own task/artifact wording favors request/response; if push stands,
  that wording wants a re-ruling rather than silence.
- **Q6 — producer-side replay on emit (A9):** bucket 5 (an invariant the emit path violates) or
  bucket 2?
- **Q7 — mnpi edge vocabulary:** is reification plus endpoint closure an acceptable realization of
  "the edge is not in the traversal's vocabulary", or must one class vary its traversal relationship
  types per principal (a new mechanism — bucket 4)?
- **Q8 — the policy-emptied marker (A6):** authorize the one measurement before mnpi/aml/ib/kyc
  build; if it leaks, bucket 5 in the disclosure layer or a deployment gate as the intended posture?
- **Q11 — the D-IMPL-49 drift (A7):** bucket 5 (widen the factory signature) or 2/6 (invoke-time
  conditioning suffices)?
- **Q13 — the capstone as written or re-scoped:** does §D step 6 require per-member children of one
  class (bucket 4, excluded pre-tag) or do group-scoped child questions satisfy it? If re-scoped,
  authorize one or two new group-scoped producer trees on the low road as example work.

**Decides launch scope**

- **Q3 — the multi-principal door (A1):** launch-ergonomics blocker or backlog? The smallest
  correction is `open_door` refusing to shadow an existing policy plus a `principals:` declaration.
- **Q4 — the credential-derived envelope (A2):** (a) accept the acquisition-seam pattern as *the*
  supported path and record the repetition; (b) ship a reference `PolicyConstraintResolver` so the
  ruled seam is a path adopters find; or (c) require one product class per perspective on this rung.
- **Q5 — the Similarity query (A3):** is a class-level lexical query with the per-alert match on the
  traversal an honest §7.4(c) demonstration, or must the rung rank acquisition-side and leave the
  headline undemonstrated? Fund the request-bound query arm?
- **Q9 — policy at the decision instant (A4):** ledger-data route acceptable, or must regime limits be
  `PolicyConstraint` artifacts resolved at `as_of`, and should `constraints_in_force` ever take the
  decision instant? Carry residual 341-1 as documented, or fund its control now that abs makes it live?
- **Q10 — several declared gates (A5):** backlog, or a launch ergonomics blocker given six rungs
  share the shape?
- **Q12 — the aggregating products' route:** abs paved with the low road only at loan grain, or the
  low road for the whole spine; close the `touched_entities` silent pass with one guard (A10)?
- **Q20 — documentation (B5):** is the public package for these clusters launch scope, as the replay
  recipe was, or post-launch?

**Decides the specs and the definitions**

- **Q2 — the A2A variant's shape** (under either reading): what "in the same process" means; whether
  the client must stay CCF-free; which harness legs; what identity is asserted (content address only,
  with a record on each side, under one `tenant_id`); confirm hw1 as the base product.
- **Q14 — kyc's review queue:** rule the product-scoped `workflow_state_ref` convention and the
  two-record linkage; carry the estate's stored resolution confidence as evidence, or recompute.
- **Q15 — the two Portfolio Management definitions:** the subject per case (a coverage book, a risk
  segment, a sponsor's companies, a trading book); principal and question per case (recommended: one
  credit-risk-officer concentration case sharing the capstone's batch, one portfolio-manager watch
  sweep sharing cp-11's); whether a scheduled sweep and a HITL exception path are inside the initial
  release contract; low road or composite; a what-if proposal in scope; whether a PM case may use
  the co-lender estate for a cross-deployment member.
- **Q16 — edge-grain invalidation:** should PM definitions avoid edge-modeled membership, or does one
  of them count as "a real product needs them" and lift the deferred limb?
- **Q17 — the co-lender's Gate 1:** which route is the Federate step (`mcp_product` recommended as
  the governed spine; peering only if the A2A variant does not already carry it); amend
  `require_attestation=false` (unexpressible) and "unattested → Context Debt" (contradicts
  D-IMPL-336); how `include_federated=false` is demonstrated; whether the reverse direction (the peer's
  agent at our door) is in scope.
- **Q18 — abs's Gate 1:** recast the granularity-disclosure gate as refuse-by-name plus a stated
  effective granularity; one role or two; whether the restricted principal's refusal names the
  privacy policy; the demonstration instant.
- **Q19 — sequencing and the three-issue cap** (§9).

---

## 9 · Recommended sequencing

**Zero SDK issues are open against the three-issue cap today** (D-IMPL-304, 341, 342 and 344 are
closed with gates; CP14-F-33 and CP06C-F-01 are ruled). The headroom is three, and batches A1–A10
are each a candidate to spend one on. The recommendation, in order:

1. **Rule the shared batches before the first T5 rung starts** — A1 (door), A2 (envelope), A3
   (similarity) and A6 (the measurement) — so mnpi, aml and ib are built once on a decided path
   rather than three times on a workaround. A4, A5 and A7 can be ruled backlog and built around.
2. **Build mnpi first**, as its spec asks: it carries the door, the envelope and the passage-similarity
   questions, and aml and ib reuse its deployment shape. Then **aml and ib** in the same batch.
3. **kyc beside them** (the HITL composition, P1), then **abs** (granularity and residual 341-1).
4. **large exposure after its group-scoped producers**, with the two PM cases after it so the
   limit-evaluate glue is written and its repetition measured (§H).
5. **co-lender after Q1 and Q17**, and the **A2A variant after Q1**; if request/response is ruled,
   A8 is one SDK phase serving both.

Optimize for coverage discovery, not example perfection: every rung above is to be built to the
minimum that drives its supported-unproven rows and records its friction, and stopped at the first
bucket-4 or bucket-5 finding (§J).

---

## 10 · What remains unverified, and where the evidence lives

**Unfinished.** The adversarial verification stage (three refutation lenses on every gap row, an
audit of every "supported" row, a challenge of every deferred row) completed only for the
portfolio-management placeholder before the credit outage ended the run; the seven vault specs and
the A2A variant carry analyst classifications with tree citations that the critic spot-checked but
no verifier attacked. What finishing it would add: for each bucket-2 row, an independent answer to
§C step 2 (the analysts leaned toward "backlog" wherever a path existed); for each supported row, a
check that the mechanism carries the spec's *exact* shape (the PM audit revised 12 of 21); for each
deferred row, a check that no SDK gap hides behind the data (the PM challenge revised 1 of 8, a
false bucket 6). The A2A variant's three bucket-4 rows were not refuted because the run stopped, but
the same finding was reached independently by the peering cluster reader, the agents cluster reader
and the co-lender analyst, and the critic confirmed the push-only reading against the tree.

**Not analyzed** (critic): nine items, each now placed — mnpi's Batch Enrich step (bucket 1), ib's
Reg FD binding (inherited), aml's BSA/AML rules (folded), the capstone's capital-base estate row, the
co-lender's institution-identity estate row, kyc's false-positive pair (estate), the A2A variant's
D-IMPL-14 drift row (Q1), and a source-side ledger time-travel caveat for aml, large exposure and mnpi
(§7). The tenth, the §D acquire-mechanism hole, is §6 item 1.

**Evidence.** `qualification/gate-0-cp15-24/evidence.tar.gz` holds, unedited: the ten capability-map
inventories, the nine analyses and the six augmented analyses (the portfolio-management file still
carries its pre-verdict buckets — read its two verdict files), the two verdict files, the synthesis
and the critic, as the agents returned them. The vault specs are canonical for the products; the
tree at `7356a0f1` is canonical for the SDK.

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
resolved by one rule each: the A2A variant's bucket-4 rows are conditional on Q1; the freshness SLA
is bucket 1 to declare and bucket 6 to enforce; materialization posture is uniformly an operations
concern; discovery is uniformly bucket 6; the multi-principal door is a bucket-1 capability plus a
bucket-2 friction row; the requested-perspective limitation applies to aml as to ib and mnpi;
several gates per class is bucket 1 by composition plus one shared §I record; the reader glue half is
carried for every rung; the "outlives the process" half of kyc's review lifecycle is bucket 6;
mnpi's zero ranking difference is a reference-index property (bucket 6), not an estate limitation;
the D-IMPL-49 drift is narrower than "never built"; the "entities only for v1" ruling is cited by
its heading (D-IMPL-334 ruling table) rather than by line; the PM fan-out row is multi-anchor
low-road aggregation, not the excluded composite fan-out.
