# Findings — cp-17-mnpi-wall-enforcement

Built 2026-09-20 on Dave's GO of the same day, against `CP-SPEC-017` (Gate 1
accepted with corrections; outcome B for the Reg FD event, selected by
ccf-dataprep's measurement). Every finding below was classified under
`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before any repair was considered,
and nothing in the SDK was repaired: findings are raised, not resolved
(`D-IMPL-261`). The close-report sections follow §K, in order, and are not
mixed. Measured passes, expected failures and sabotage outcomes are reported
separately from each other and from the count of declared gates.

**Measured at close (2026-09-20, live estate, `CCF_REQUIRE_ESTATE=1`):**
21 gate tests **passed**, 0 failed, 3 **xfailed** (strict; each names its
finding), 0 skipped, in four modules under `tests/examples/test_cp_17_*.py`.
`tools/check_product_gates.py`: 21 declared, 21 executing. `make lint` rc 0.
The always-on structural gates (artifact headers, README template, spine
separation, algorithmic, the gate-shape rosters) pass.

## 1 · SDK capability proven

| launch-contract item (§D) | how this tree exercised it |
|---|---|
| define contracts as Control Plane artifacts | one `ccf_config.yaml` declares the class, the four operators, the request contract with a relative default, the λ_c table, the debt profile, the policy bundle, the door; `open_product` refuses a half-declared gate by name |
| assemble through the single writer and the declared operators | acquisition emits envelopes, edges first; every claim enters through L2; the plan is the SDK's set passed through (`MWE-G05`) |
| apply authorization and policy before use | the door decides the perspective from the credential; the envelope is computed at the acquisition seam from `context.perspective`; Policy runs first (`MWE-G02`, `MWE-G03`, `MWE-G05`, `MWE-G06`, `MWE-G08`) |
| preserve product identity and content addressing | three principals, three addresses (`MWE-G01`); door and in-process byte-equal; two door calls one address and one record (`MWE-G18`) |
| calculate Context Debt correctly | supersede-only classes read 1 beside a curve class on `valid_from`; C over the principal's own required classes (`MWE-G12`, `MWE-G20`) |
| refuse correctly, as data, with a replay reference | the ungranted principal, the requested role outside the grant, the tolerance, the declared gate, the invalidation boundary — every one a `RefusalEnvelope` with a record (`MWE-G03`, `MWE-G11`, `MWE-G14`, `MWE-G15`) |
| preserve sufficient refusal evidence | the ungranted principal's record keeps `principal-not-entitled` / `no-projection-plan` while the wire shell shows only the withheld markers (`MWE-G14`, `MWE-G17`) |
| replay and reconstruct | the three products rebuild byte for byte; the refusal reconstructs (`MWE-G17`) — with two recorded gaps (§4) |
| local and remote producer boundaries | in-process, the standard MCP door and the HTTP door serve one opened product (`MWE-G15`, `MWE-G18`) |
| prevent identity masquerading | the perspective resolver proposes; the entitlement source decides; a requested role outside the grant is refused, never downgraded (`MWE-G15`) |

Beyond the launch contract, first on the ladder: several credentialed
principals behind one shipped door; an operator-bounding set sourced from
the credential rather than the effective request; all four operator
categories on one domain rung with Similarity behind Policy; the
departmental SQLite as a source read first; the two-clock wall question
answered from the control room's own record; the A6 property as a product
gate (`MWE-G16`).

## 2 · SDK friction observed (§E) — the DX rubric (Gate-0 §5.0)

Counts measured on the tree at close (`physical` lines / non-comment, non-blank):

| region | files | physical | non-comment |
|---|---|---|---|
| plumbing | `produce.py`, `server/serve.py` | 207 | 159 |
| domain | `deployment.py`, `acquisition.py`, `projection.py` | 931 | 731 |
| presentation | `run.py` | 118 | 96 |
| documents | `ccf_config.yaml`, `ccf_environment.yaml`, `artifacts/*.yaml` | 583 | 379 |

Distinct `ccf`/`ccf_runtime` names imported by the tree: **34**. Private
(underscore) SDK symbols in the tree: **0**; in its tests: **1**
(`GovernedResolver._operator_parameters`, inside the hand-built replay
environment — `CP17-F-06`, inherited).

**The three batch-1 patterns, on the eight counts, each placed in one of the
four classes** (easy → keep; repetitive → backlog; substantial repeated
plumbing or private knowledge → candidate ergonomics issue; correctness
depends on hand-wiring → launch concern):

| count | A2 · credential-derived envelope (2nd instance) | A1 · several principals, one door (1st) | A3 · policy before similarity over a corpus (1st with the SDK operator) |
|---|---|---|---|
| domain LOC | the envelope rule (`admitted`, `_over_wall`, `required_classes`, the plan read) ≈ 70 in `acquisition.py` | 0 | 0 — the query, floor, corpus attribute and index version are one `operators:` block |
| plumbing LOC | ≈ 25 in `deployment.py` (the `AcquisitionContext` → `acquisition.acquire` call, the `GovernedRefusalRaised` conversion) | ≈ 75 in `server/serve.py` (token source, resolver, `entitle`, `open_wall_door`, `http_app`) | 0 |
| copied patterns | the acquisition-seam entitlement shape of cp-13-canonical, rewritten a second time | the `_mcp_server` fixture shape of `tests/mcp/test_egress_parameters.py`, the `_entitled` shape of `tests/http_api/test_product_entitlement.py` | none |
| hand-built Control Plane / runtime objects | 0 | **3** for the MCP door (`StaticTokenSource` + `SourceBackedTokenVerifier`, the resolver, `ProductEntitlementPolicy` with its grants) + **3** for HTTP (`BearerTokenAuth`, `ControlPlaneProductEntitlementSource`, `ApiDependencies`) — the door's predicted 3, measured 3 | 0 |
| private symbols | 0 | 0 | 0 |
| configuration duplication | **1** — `artifacts/perspectives.yaml` restates, as the product's declared shape, what the estate's `projection_plan` rows already say | **1** — the door's own one-principal policy sits under the tenant key beside the deployment's three-grant policy (two versions; `ConstraintEffectivityConflict` latent, dormant because no request names `policy_overrides`) | 0 |
| concepts not on the public surface | that `AcquisitionContext.perspective` is the only seam by which the credential reaches an operator's bound; that the Policy operator's permitted set is class-level; that `observed_time` is the claim's `valid_from` and the freshness basis; edges before nodes | the latest-wins registration order; `requested_role=None` on both MCP doors; the four-axis tool with the canonical `request` copy; `STATUS_BY_KIND` keyed by the kind string; the HTTP `role` query parameter | that the corpus is read from the pre-operator view; that a ranked class absent from the corpus map is silently omitted; that per-hit scores do not reach Π (no top-k possible in Π) |
| AI-generatable from the spec plus public guidance? | **partly** — the seam is documented in docstrings; the class-level Policy set and the two-axis rule are the spec's | **no** — the three overrides and the ordering rule are not on a public page; the HTTP composition is a test's shape | **yes** for the block; **no** for knowing the score never reaches Π |
| class | **candidate ergonomics issue** (repeated plumbing + private knowledge), per the A2 ruling: measured, not generalized; decide at the third instance (AML) | **candidate ergonomics issue** (private ordering rule + duplicated authority); step 2 of §C answered "candidate" at Gate 0 and the measurement agrees | **repetitive but understandable** → backlog: the block is small; the missing per-hit score is `CP17-F-04`'s cause |

The target chain (requires → grant → registration → mapping → governed
child) does not apply to a producer with no child; the departures measured
above are all on the producer's own boot.

**Relocated, not eliminated.** The wall's per-principal narrowing lives in
`acquisition.py` because the SDK offers no seam by which the credential can
reach the Policy operator without becoming a caller's claim (Gate-0 A2/B1).
The Policy operator is therefore the class-level containment guarantee
(`MWE-G06` proves it live) and not the per-principal wall.

## 3 · Launch blockers

None newly raised — which is not "no launch blockers": the two replay gaps
in §4 are §B.1-shaped ("a served product's lineage cannot be reconstructed
from its replay record") and are raised for a decision rather than
classified here; the examples are probes (`D-IMPL-261`).

## 4 · Backlog candidates (§I) and findings raised

| id | finding | class (§B) | disposition |
|---|---|---|---|
| `CP17-F-01` | **The credential-derived envelope is acquisition-seam plumbing** (measured above: ≈ 70 domain + ≈ 25 plumbing lines, 0 objects, 1 duplication, 4 undocumented concepts). Second instance after cp-13-canonical. | candidate §B.2 | counted; the A2 review decides after AML's third instance |
| `CP17-F-02` | **The supervisor's side is out of scope**: no wall-decision attribute is written into any principal's fabric or record; the estate declares no supervisor principal or plan. Gate-0 row 47 stays a backlog record. | §B.4 | disclosed in the spec and README |
| `CP17-F-03` | **The containment / no-disclosure gate is the fourth example-level writing of one** (cp-01, cp-02, cp-11, here): `wall_gate` folds three predicates under one slot. | §B.3 (backlog §I) | the §H threshold is reached; recorded, not built |
| `CP17-F-04` | **The ranking-difference number is zero by construction**: SP Plus holds no draft; and per-hit scores do not reach the view, so Π cannot rank or cut — the Similarity operator acts as a floor filter. The spec's Π-side top-k is therefore **not implemented** (F.2 row 3 closed as a finding). | §B.3 + §B.4 (two halves) | the score-on-the-view half joins Gate-0 A3's backlog |
| `CP17-F-05` | Wall state, the restricted list and embargo windows carry no λ_c row; they are envelope inputs. Their currency is disclosed against the pinned instants. | §B.4 | disclosed |
| `CP17-F-06` | The replay environment is hand-assembled in the tests (~40 lines, one private reach) — `CP06C-F-01` inherited. | §B.3 | carried |
| `CP17-F-07` | Requesting a perspective is HTTP-only; over MCP the channel does not exist. | §B.3 | disclosed |
| `CP17-F-08` | **A computed-empty serve cannot be rehydrated through the public replay seam.** `ContentGenerationPath` carries no `computed_empty`; `replay()` raises `ReplayDivergence` on the nonexistent-LEI serve at tolerance 1.0. Kept executable as `tests/examples/test_cp_17_replay.py` (`test_a_computed_empty_serve_replays_through_the_public_seam`, xfail strict). | **§B.1-shaped — raised for a decision** | not repaired; the launch contract's "replay and reconstruct" is exercised on the three role products and the refusal (`MWE-G17`) |
| `CP17-F-09` | **A refusal raised at the acquisition seam on a fresh Control Plane cannot be replayed**: its dimension-2 bindings pin the request-contract version that the resolver registers only on the served path, so the first question of a fresh product leaves a record `replay_refusal` cannot resolve. Executable as `test_a_refusal_asked_first_of_a_fresh_product_reconstructs` (xfail strict). | **§B.1-shaped — raised for a decision** | not repaired; `MWE-G17` serves a product first, then reconstructs the refusal |
| `CP17-F-10` | **The declared gate's ceiling travels with the candidate.** `wall_gate` reads `permitted_edge_types` off the payload's `plan` member, which acquisition wrote from `context.perspective`; an acquisition keyed to another principal carries that principal's plan and is SERVED under the asking role. The gate seam receives no `Perspective`, so a containment gate cannot verify the credential independently. Executable as `test_an_acquisition_keyed_to_another_principal_is_not_refused` (xfail strict). | §B.2 candidate (a gate with no access to the decided perspective) | recorded as a backlog record: "the declared product gate receives the decided perspective" |
| `CP17-F-11` | **An unreachable control room is a raise, not a governed refusal** (`acquisition.ControlRoomUnreachable` propagates through `opened.answer`; over the door it is a `ccf-runtime-failure`; no record is written). `CP13C-F-03` class, ruled "not changed" at `D-IMPL-304`. | §B.3 (carry) | disclosed; `MWE-G09` asserts the raise for every principal |
| `CP17-F-12` | **F is a mean over every observation in the view, so supersede-only classes dilute a curve class.** BGC (16 family members reading 1) serves fresher than SP Plus (no family) although its position is a day older. The Standard's §E.2 asks F to be normalized over required signal classes; the reference scorer averages over observations present. `MWE-G12` asserts only what holds (AHR ≥ SP Plus; banker and analyst exactly 1). | §B.2 candidate (SDK-versus-Standard divergence) | recorded for a decision; never re-pinned |
| `CP17-F-13` | **An empty view is withheld at the class default tolerance**: nothing admitted reads C = 0, so D_c = 1 and the default 0.80 withholds it as `tolerance-exceeded`; the nonexistent subject and the policy-emptied subject refuse identically there and serve identically (computed-empty) at tolerance 1.0. `MWE-G16` asserts both paths. | §B.4 (a product-design consequence, not an SDK defect) | the spec's G16 statement is restated |
| `CP17-F-14` | **The plan's classification envelope bounds the document and MNPI-tagged classes, not desk data.** Read literally over every class, the trader's plan (`public-filed` only) excluded its own positions; `source-vocabulary.yaml` now declares the bounded classes and the gate's second predicate follows it. Spec §D.3 step 1.5 refined. | §B.4 (spec refinement) | disclosed |
| `CP17-F-15` | **The spec's G07 sabotage could not go red as written**: an injected draft carries a classification inside the class-level vocabulary, so the Policy operator admits it — the wall is at acquisition. G07 is restated as ordering + out-of-vocabulary containment + the served research being a subset of what acquisition admitted. | §B.4 (spec restatement) | disclosed |
| `CP17-F-16` | **`artifacts/assembly-recipe.yaml` is not shipped.** The delivery recipe and spec §G.2 item 4 require it with a witness per step; none of the four canonical/paved trees ships one and the only witness resolver is cp-00's. The precedent was followed and the conflict is surfaced for Dave rather than resolved silently. | conflict surfaced | Dave's call |
| `CP17-F-17` | **A recorded invalidation boundary blocks every forensic ask before it.** The register is Control Plane state across questions; once the Reg FD boundary is recorded for the issuer, every later question whose `asked_at` precedes it and touches the issuer refuses — TW and T0 included. A deployment that pre-recorded known historical events at open could never answer a forensic question. The boundary is therefore recorded by the test (`MWE-G11`) after the forensic serves, not at open. | §B.3 (design note on `D-IMPL-334`) | recorded |
| `CP17-F-18` | **The principal's plan version rides on the payload, not on the lineage pin.** No per-principal artifact is registered in the Control Plane; `policy_bundle_versions` carries one hash for all three roles. The served principal's own plan id and version are in the hash-bound `plan` member (`MWE-G13` restated; F.2 row 14 closed). | §B.4 | disclosed |
| `CP17-F-19` | `ServedProduct.replay_ref.content_address` is the replay RECORD's address; the product's own address is `content_hash(product)` (and `record.content_generation_path.product_content_address`). A naming surprise, no defect. | DX note | recorded |
| `CP17-F-20` | Two door calls with one credential and question return one content-addressed replay record; a reader expecting one record per call is surprised. | DX note | recorded |

## 5 · Estate / example limitations (§B.4)

Disclosed where the reader meets them (spec §C.4, README):

- `REGFD-000` designates no records (outcome B; ccf-dataprep 2026-09-20); its provenance label reads `synthetic — internal`, arguably one class too weak; cited as measured.
- No issuer-level market data exists anywhere; the trader's product carries positions and no price series.
- Blackout windows do not exist; the one "insider" node is a Regulation O designation.
- SP Plus has no `owns`/`controls` edges, so its `family` member is empty; the walk's family vocabulary is exercised on the trader's freshness subjects (AHR, BGC) only.
- Drafts and published notes never coexist on one issuer; every embargoed note stays `draft`; MNPI interactions have no participants.
- The four restricted-list rows are positionally assigned by the loader; read-only, never re-run.
- The position `as_of` is date-grained; the 24-hour half-life is illustrative (`D-IMPL-323`).
- The estate declares no supervisor principal; the coverage manifest (ccf-dataprep `6a8fb4c`) exits 1 by design with two GAP rows.

## 6 · Product result

At `T1 = 2026-08-17T00:00:00Z`, SP Plus (`0IDE18EMH1CUKQCUYE69`), three
principals, one door: the coverage banker's product carries four deal
engagements (two MNPI-bearing, keyed by `WALL-000`) and forty-two
interactions under `hasDealEngagement`, `hasInteraction`, `hasMnpiEngagement`;
the research analyst's carries the published notes the lexical floor kept
under `hasPublishedResearch` and nothing of the engagements; the trader's
carries one position under `hasPosition`. Three content addresses; one
schema, one `plan_id`, one operator set. Debt: banker and analyst read
freshness 1 and D_c 0; the trader reads D_c 0.25 on SP Plus (`ok`).

At `TW = 2026-03-10` the banker's product carries no MNPI engagement with
the control room's knowledge of that day and carries it with the knowledge
of 2026-03-20. At `T0 = 2026-07-01` the issuer's `reg_fd_disclosure` is null;
at `T1` it carries the event. The ungranted credential is refused on both
doors with the minimal shell and a replay reference; a requested role outside
the grant is refused, never downgraded. A nonexistent issuer is withheld at
the class default tolerance and served computed-empty at tolerance 1.0,
identically to a policy-emptied subject.

**What a consumer can rely on:** the member set of its role, fixed; every
served item inside its own plan's vocabulary and classification envelope;
the `reg_fd_disclosure` member as a dated public-filed fact; the content
address as identity across doors. **What it cannot rely on:** any statement
about what was withheld (none is made); a per-issuer price series (none
exists); replay of a computed-empty serve or of a refusal asked first of a
fresh product (`CP17-F-08`, `CP17-F-09`); the freshness factor as a
per-class number (`CP17-F-12`).

## Sabotage record

Every gate's `sabotage` and `observed_red` are in `artifacts/gates.yaml`.
Summary: 21 declared; **16 observed red** by a sabotage run on 2026-09-20 —
nine by in-memory mutation of real estate answers fed to the test function
(`MWE-G01`, `G02`, `G04`, `G05`, `G08`, `G10`, `G13`, `G20`, `G21`; the tree
untouched), seven by a scratch copy of the tree or test with one mutation
(`MWE-G03` with the gate replaced by a pass-through, `G11` with the boundary
never recorded, `G14` with every principal granted, `G15` with the requested
role ignored, `G17` with a re-derived debt, `G18` with a per-call counter,
`G19` with the crossing id written onto the issuer claim); **5 not
individually sabotaged** and recorded `observed_red: null` (`MWE-G06`,
`G07`, `G09`, `G12`, `G16` — three of them carry their sabotage inline, as
the test's own wrapper of `acquire`, so the red state is the test's
construction rather than a mutation of the tree). `MWE-G18`'s sabotage also
reddens `MWE-G15`'s byte-equality clause and is not isolable by
construction. **Three strict expected failures** keep `CP17-F-08`, `F-09`
and `F-10` executable; none is a passing assertion.

## Security remediation — `EX-01`, `EX-09` (2026-10-07)

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before the change: §B.4, the example's own code rather than the SDK. Changed under `D-IMPL-261`'s "objectively wrong" reason, authorized by `D-IMPL-376` ruling (7): *"SDK input rejection is useful defense, but leaves fragile example code for adopters to copy."* The SDK half — `ProductRequest.subject` had no shape — was closed by `D-IMPL-357`'s subject floor, which refuses these values at the door; the guard here holds in-process, below it.

- **`EX-01`.** `acquisition.py::_over_wall`, `::_reg_fd` and `::_family` spliced the subject LEI — and, in `_over_wall`, the verified principal — into `FILTER` string literals by f-string. Each value now passes through `acquisition.py::_literal`, which refuses — never escapes — any text a SPARQL string literal cannot carry unescaped (`"`, `\`, any control character), before any store is read. Every one of these reads already sat behind the bound issuer lookup in `acquisition.py::acquire` (ruling C6's regrade); the guard does not rely on it.
- **`EX-09`.** `acquisition.py::_Relational.rows` built `SET search_path TO {schema}` by f-string (security review 2026-09-23). It now composes the statement with the driver's own `psycopg.sql` — `SQL("SET search_path TO {}").format(Identifier(schema))` — so the configured schema reaches PostgreSQL as one quoted identifier, whatever it contains. The documented schema `ccf_v2` is one lowercase identifier, so it names the same schema quoted or not.

No served output moves: for every value the guard admits, the query text is byte-identical to before (measured on the demonstration subjects). Evidence: `tests/examples/test_ex_01_sparql_value_placement.py`, `tests/examples/test_ex_09_search_path_identifier.py`.
