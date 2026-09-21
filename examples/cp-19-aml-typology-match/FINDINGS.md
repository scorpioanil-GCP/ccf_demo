# Findings — cp-19-aml-typology-match

Built 2026-09-20 against `CP-SPEC-019`, on the tightened coverage path: the
issue cap re-baselined to 0 of 3, the four stop conditions in force, and the
mandatory A2 third-instance measurement (§2) as the reason this rung was
built third. Every finding below was classified under
`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before any repair was considered,
and nothing in the SDK was repaired: findings are raised, not resolved
(`D-IMPL-261`). The close-report sections follow §K, in order, and are not
mixed. Measured passes, expected failures and sabotage outcomes are reported
separately from each other and from the count of declared gates.

**Measured at close (2026-09-20, live estate, `CCF_REQUIRE_ESTATE=1`):**
17 tests **passed**, 0 failed, 2 **xfailed** (strict; each names the finding
it keeps executable), 0 skipped, in four modules under
`tests/examples/test_cp_19_*.py`. 14 gates declared, 14 claimed by an
executing test; the remaining two passing tests exercise the doors and claim
no gate (`ATM-F-14`). Thirteen of the fourteen gates were observed RED under
their own sabotage; `ATM-G01` is `unavailable` with its guard named.

**Active SDK issue cap: 0 of 3.** No launch blocker, no missing AML-required
capability, no incorrect SDK behavior and no security or governance defect
was found. Two previously recorded gaps reproduced here as second instances
(§4, `ATM-F-10` and `ATM-F-11`); reproducing a recorded gap is carrying it,
not charging a new one.

## 1 · SDK capability proven

| launch-contract item | how this tree exercised it |
|---|---|
| define contracts as Control Plane artifacts | one `ccf_config.yaml` declares the class, the four operators, the request contract with a relative default, the λ_c table, the debt profile, the policy bundle, the door |
| assemble through the single writer and the declared operators | acquisition emits envelopes, edges first, attributed nodes last; every claim enters through L2; the plan is the SDK's own set passed through |
| apply authorization and policy before use | the envelope is computed at the acquisition seam from `context.perspective`; the departmental store is read before any enterprise source; Policy runs first (`ATM-G01`, `ATM-G02`, `ATM-G09`, `ATM-G10`, `ATM-G11`) |
| preserve product identity and content addressing | three perspectives, three addresses, one schema and one `plan_id` (`ATM-G07`, `ATM-G13`) |
| calculate Context Debt correctly | seven supersede-only classes beside one curve class on `valid_from`; C over the perspective's own required classes read from its plan |
| refuse correctly, as data, with a replay reference | the forbidden disposition, the unmapped perspective, the tolerance — each a `RefusalEnvelope` with a record (`ATM-G04`) |
| preserve sufficient refusal evidence | the declared gate's breach names the disposition and the gate clause in `assembly_refusal` (`ATM-G04`) |
| replay and reconstruct | the three adjudications rebuild byte for byte with the posture that governed, the perspective's shape and the advisory passages; a replay handed a different posture instant diverges (`ATM-G13`) — with the two recorded gaps in §4 |
| local and remote producer boundaries | in-process, the standard MCP door and the HTTP door over ONE opened product, measured: four credentials through the MCP door give three perspectives, three addresses and three shapes with the fourth refused, and the HTTP door's bytes for a perspective's own role are identical to the MCP door's (`ATM-F-14`) |
| prevent identity masquerading | the request surface carries no `perspective`; the resolver proposes and the entitlement source decides |

First on the ladder at this rung: **a bound computed before the thing it
bounds** — the permitted disposition set is read from the posture and its
rules before any candidate exists, and the candidate list is generated from
it, so containment is by construction rather than by filter (`ATM-G03`,
`ATM-G04`). Also first: **restricted existence rather than restricted
content**, where a member is absent from a perspective's product rather than
empty in it, and the absence is doubly enforced (`ATM-F-08`).

## 2 · The A2 third-instance measurement — MANDATORY, and the reason this rung was built

`A2` is the credential-derived policy envelope: a permitted set or a request
default sourced from the verified grant. Its Gate-0 prediction was
**"substantial repeated plumbing plus private knowledge → candidate SDK
ergonomics issue"**, with the ruling: build mnpi and aml on the existing
mechanism, measure at the third instance, decide then. This is that
measurement. **It is a measurement and a recommendation, not a decision.**

The three instances, on the seven dimensions. All LOC figures are physical
lines / non-comment non-blank lines, measured by AST span on 2026-09-20.

| dimension | cp-13-canonical (1st) | cp-17 mnpi (2nd) | **cp-19 aml (3rd)** |
|---|---|---|---|
| **domain-policy LOC** — the envelope rule itself | 64 / 56 (`Entitlement`, `_entitlement`, `ScopeNotEntitled`) | 58 / 57 (`plan_for`, `principal_roles`, `required_classes`, `_over_wall`, `admitted`) | **55 / 54** (`_visible_sars`, `plan_for`, `required_classes`, `_residency_entitlement`) |
| **generic plumbing LOC** — the seam | 22 / 21 (`deployment.acquire`) | 22 / 20 | **25 / 22** |
| **concepts absent from public docs** | 4 | 4 | **4, the same four** — plus 1 new one that is not A2's (`ATM-F-05`) |
| **hand-built runtime objects** | 0 on the envelope | 0 on the envelope (3 + 3 belong to A1, the door) | **0 on the envelope** (3 + 3 for the door, identical to cp-17) |
| **duplicated authority** | 0 | 1 | **3** — and two of the three are this product's own design choice (`ATM-F-09`) |
| **structural similarity** | — | — | **measured, below** |
| **AI-generatable from the spec plus public guidance?** | no | partly | **partly — unchanged** |

### The structural-similarity measurement, which is what decides this

Whether an abstraction is owed turns on whether the repeated thing is *code*
or only *shape*. Measured with `difflib.SequenceMatcher` over comment- and
docstring-stripped code lines:

| compared | ratio | identical lines |
|---|---|---|
| cp-19 `plan_for` vs cp-17 `plan_for` | 0.33 | 4 of 8 |
| cp-19 `required_classes` vs cp-17 `required_classes` | 0.09 | 1 of 15 |
| cp-19 `_visible_sars` vs cp-17 `_over_wall` | 0.07 | 1 of 14 |
| cp-19 `_residency_entitlement` vs cp-13-canonical `_entitlement` | 0.00 | 0 of 7 |
| **cp-19 `deployment.acquire` vs cp-17 `deployment.acquire`** | **0.71** | **15 of 22** |
| cp-19 `deployment.acquire` vs cp-13-canonical `deployment.acquire` | 0.51 | 9 of 22 |

**The finding is a split, and it goes the opposite way on the two halves.**

- **The domain half is not repeated at all.** Three rungs, three envelopes,
  and no two share more than a third of their lines — usually under a tenth.
  Each reads a different table, keyed differently, returning a different
  type, refusing on a different condition. The *shape* recurs; the *code*
  does not. An abstraction over this half would have to be parameterized by
  everything that differs, which is everything.
- **The seam half IS repeated, and it is small.** `deployment.acquire` is
  15 identical lines out of 22 across the second and third instances: unpack
  the effective request, call the tree's `acquire`, convert the tree's
  absence exception into a `GovernedRefusalRaised`, hand back envelopes.
  That is the whole repetition. It is 15 lines, not a subsystem.

**Against the prediction:** "substantial repeated plumbing" is **not
confirmed** — the repeated plumbing measures 15 lines. "Private knowledge"
**is** confirmed: the same four undocumented concepts were needed a third
time, unchanged and none of them on a public page. Those four are:

1. `AcquisitionContext.perspective` is the only seam by which the verified
   credential can reach an operator's bound without becoming a caller's claim.
2. The Policy operator's permitted set is **class-level**, not per-principal,
   so the per-perspective narrowing must happen before the operator runs.
3. `observed_time` on a `SignalEnvelope` is the claim's `valid_from` and is
   the freshness basis for a `decay_basis: valid-from` class.
4. Edges are emitted before attributed nodes, because a thin endpoint claim
   minted by an edge supersedes a richer claim at the same URI if it arrives
   after it (`D-IMPL-316`).

### Recommendation: **B** — backlog, no SDK abstraction

**A** (keep the existing path, nothing owed) understates it: the same four
concepts had to be rediscovered three times, and that is a real cost.
**C** (a measured proposal for a new SDK abstraction) is not supported by
the measurement: the only genuinely repeated code is 15 lines of seam glue,
and an abstraction over the domain half would be parameterized by
everything that differs between the three rungs. Building it would trade 15
duplicated lines for a new configurable surface — the shape this project
refuses elsewhere, and the shape `D-IMPL-261`'s "a new example never earns a
redesign because another design is cleaner" names directly.

**B**, with two named carries:

- The private-knowledge half routes to **B5** (the adopter-facing
  documentation backlog), not to a new mechanism. Under Q20's ruling
  documentation completeness is not to become another pre-release project;
  what this measurement adds is that these four concepts, specifically, are
  the ones a fourth rung will need and will not find. They are cheap to
  write down and expensive to rediscover.
- The A2 count continues on `ib` and `kyc` with the same seven dimensions.
  If the seam half grows materially past 15 lines, or if a fourth rung needs
  a fifth undocumented concept, the classification should be revisited.

**No SDK change is pre-authorized by this section, and none is requested.**

## 3 · Launch blockers

None raised. The two §B.1-shaped replay gaps in §4 are reproductions of
findings CP-17 already raised for a decision; this rung adds that they are
properties of the paved road rather than of one tree, which is evidence for
that pending decision and not a new charge against the cap.

## 4 · Findings raised

| id | finding | class (§B) | disposition |
|---|---|---|---|
| `ATM-F-01` | 0 of 72 advisory passages carry an embedding or a `sha256`; the vector path is unreachable and anchoring uses the passage id. | §B.4 estate limitation | disclosed in the spec, `ccf_config.yaml` and the README; the ranking is lexical and the index version is pinned |
| `ATM-F-02` | Three vocabularies for jurisdiction: the residency constraint names countries in full, parties carry ISO3, principals carry ISO2 prefixes. The binding evaluates the DECLARED entitlement and invents no country mapping. | §B.4 estate limitation | disclosed; `ATM-G11` asserts the containment that holds |
| `ATM-F-03` | `ccf_v2.aml_projection_plan` is keyed by PERSPECTIVE and carries assembled elements, not permitted sets — a different envelope shape from cp-17's per-principal plan, and the estate holds no AML principal at all. | §B.4 + example decision | resolved by deployment declaration (`TBC-1`): the credential → perspective half is named in `ccf_environment.yaml`, the perspective → plan half is read from the estate. An A2 input, counted in §2 |
| `ATM-F-04` | `CP17-F-12`'s scorer semantics apply here unchanged: F is a mean over every observation in the view, so seven supersede-only classes dilute the one curve class. | §B.2 carried | never re-pinned; no debt figure is asserted as a number |
| `ATM-F-05` | **The reference Similarity index's usable score band collapses for a short query over long passages.** `minimum_score_percent` is on a 0..100 scale; `TokenOverlapIndex` scores integer Jaccard overlap, so a 7-token query against passages of ~90 unique tokens produces a four-value band — measured over the whole 72-passage corpus: {3: 1, 2: 5, 1: 22, 0: 44}. Any floor of 2 or more removes every passage the demonstration alert's typology anchors; only 1 discriminates. A deployment setting what reads like a mild 5 percent floor silently gets an empty corpus and no signal that it did. | §B.3 friction / DX note | disclosed at the declaration site with the measurement, in the README, and here. Not worked around: the floor is the smallest value at which the term still moves, per CLAUDE.md §9 |
| `ATM-F-06` | No alert's subject party has a row in the sanctions screening table (measured: the join returns zero rows estate-wide). `sanctions_screening` is a structurally present, permanently empty member of two perspectives' products. | §B.4 estate limitation | disclosed; it is a correct demonstration of "present and empty is not absent", and the classification walk over that member is vacuous |
| `ATM-F-07` | **A sabotage that cannot redden its gate is not a sabotage.** `ATM-G08`'s first sabotage — make a member conditional on the alert — left the gate GREEN, because the two demonstration alerts have the same empty members for the examiner, so any shape-varying mutation produced the same shape twice. The comparator was replaced with an alert whose content genuinely differs, and the test now asserts that difference as its own positive control. | proof-machinery defect, mine | corrected before close; recorded rather than quietly fixed |
| `ATM-F-08` | **The L1 analyst's silence about a SAR is doubly enforced, and either guard alone suffices.** Breaking the departmental audience filter left `ATM-G09` green: `l1`'s estate projection plan does not carry `sar_filing_history`, so the class is never minted whatever the audience says. Both guards plus the declared shape had to be broken together to leak. | a property, measured | recorded as a property of the design; the gate's sabotage now names both guards |
| `ATM-F-09` | The classification vocabulary is declared in **three** artifacts — `ccf_config.yaml` (the Policy operator's permitted set), `artifacts/source-vocabulary.yaml` (the per-class assignment and its vocabulary) and `artifacts/perspectives.yaml` (the declared gate's authority). Two of the three are this product's own choice, not the SDK's requirement. | §B.3 example decision | recorded; each site is load-bearing for a different reader, and `ATM-G02`'s sabotage had to edit two of them to produce one out-of-vocabulary item |
| `ATM-F-10` | **`CP17-F-08`, second instance.** A computed-empty serve cannot be rehydrated through the public replay seam: `ContentGenerationPath` carries no `computed_empty`, so `replay()` raises `ReplayDivergence` on the nonexistent-alert serve at tolerance 1.0. Measured here with the same cause and a different tree. | §B.1-shaped, raised for a decision by CP-17 | not repaired; kept executable as a strict xfail. This rung's contribution is that it is not tree-specific |
| `ATM-F-11` | **`CP17-F-09`, second instance.** A refusal recorded at the acquisition seam on a fresh Control Plane cannot be replayed: its dimension-2 bindings pin the request-contract version the resolver registers only on the served path. `ReplayUnresolvable` names the exact artifact key. | §B.1-shaped, raised for a decision by CP-17 | not repaired; kept executable as a strict xfail |
| `ATM-F-12` | The replay environment is hand-assembled in the tests (~70 lines, one private reach — `GovernedResolver._operator_parameters`). `CP06C-F-01` / `CP17-F-06`, third instance. | §B.3 carried | carried; the tree itself reaches no private symbol |
| `ATM-F-14` | **The specification declares no door gate.** `CP-SPEC-019` §G.1 declares fourteen gates, all of them about the product; the tree nonetheless ships a standard MCP door and an HTTP door, because the estate holds four credentials and the perspective is the door's. A shipped door that nothing opens passes every test there is (`D-IMPL-324`). Two tests in `tests/examples/test_cp_19_door.py` therefore exercise both doors and **claim no gate**: three credentials receive three perspectives, three addresses and three shapes; the ungranted fourth is refused with the minimal shell and a replay reference, and the wire shell names neither the principal, nor `no-projection-plan`, nor the unmapped perspective; over HTTP a requested perspective outside the grant is refused with the same shell rather than downgraded, and the same credential asking for its own role receives bytes identical to the MCP door's. | §B.4 spec gap, surfaced not resolved | the gate roster is the specification's and was not widened to suit the tree; the measurement is kept executable instead |
| `ATM-F-13` | The posture bound (`posture_at`, `permitted_dispositions`, 47 / 46 lines) is a *second* envelope pattern in this tree, keyed on `as_of` rather than on the credential. It is not A2 and is counted apart in §2 so the A2 figures are not inflated by it. | measurement hygiene | recorded |

## 5 · Estate / example limitations (§B.4)

Disclosed where the reader meets them:

- No advisory passage carries an embedding or a `sha256` (`ATM-F-01`).
- No alert's subject party has a sanctions screening row (`ATM-F-06`).
- The estate declares no AML principal; the credential → perspective mapping
  is this deployment's, named in `ccf_environment.yaml` (`ATM-F-03`).
- No perspective holds the residency entitlement, so `ATM-G11` measures the
  containment that holds rather than the admission that would follow a grant;
  60 of the demonstration alert's 200 network parties are removed by it.
- Transaction value dates are date-grained; the 86,400-second half-life is
  illustrative and the freshness term is asserted directionally, never pinned.
- The Similarity floor of 1 is illustrative, with its measured distribution
  recorded at the declaration site (`ATM-F-05`).

## 6 · Product result

At `asked_at = 2026-08-25T00:00:00Z`, alert `ALT-000021` (subject party
`AMLP-0023`, typology `TYP-STRUCT`): the L1 analyst receives typology
matches, disposition candidates and an empty sanctions screening, and no
member, count or byte naming the SAR the estate holds against that alert;
the L2 reviewer receives the counterparty network, the ownership chain, the
prior-alert lineage and the `restricted` SAR, and no disposition candidates;
the examiner receives all of it plus policy-version attribution and the
reasoning trail with its advisory passages. Three shapes, three content
addresses, one schema and one `plan_id`.

Asked at the earlier posture instant the permitted set differs from the
later one, and each perspective's candidates fall inside its own instant's
bound. Asked about the confidential-SAR alert, the filing reaches the
examiner and not the L2 reviewer. An alert id no row answers is withheld at
the class default tolerance and served computed-empty at tolerance 1.0,
path-for-path identical to an alert whose admissible content Policy removed
entirely.

**What a consumer can rely on:** the member set of its perspective, fixed
for every alert; every candidate inside the permitted set the posture in
force at `as_of` computed; every served item inside the declared
classification vocabulary; the content address as identity. **What it cannot
rely on:** any statement about what was withheld (none is made); a sanctions
screening result (none exists in the estate); replay of a computed-empty
serve or of a seam refusal asked first of a fresh product (`ATM-F-10`,
`ATM-F-11`); the freshness factor as a per-class number (`ATM-F-04`).

## The doors, measured

Not a gate, and recorded here because the tree ships them
(`ATM-F-14`). Four credentials, one standard MCP door, one question, one
instant:

| credential | outcome |
|---|---|
| the L1 analyst | served; `sar_filing_history` absent from its shape |
| the L2 reviewer | served; a different address and a different shape |
| the examiner | served; a third address and the largest shape |
| the recognized credential with no grant | refused, `subject-unavailable` at `minimal` disclosure, with a replay reference and no mention of the principal, the missing plan or the unmapped perspective |

Over HTTP, against the same opened product: the L1 analyst requesting the
examiner's perspective is refused 404 with the same minimal shell and the
refusal does not echo the role it refused; the same analyst requesting its own
role is served 200 with bytes identical to the MCP door's; an unrecognized
credential is 401 `unauthenticated`.

## Sabotage record

Every gate's sabotage and the red it was observed at are in
`artifacts/gates.yaml`. Summary: 14 declared; **13 observed RED** by a
sabotage run on 2026-09-20 — ten by a single reverting edit to the tree with
only that gate's test executed, and three (`ATM-G04`, `ATM-G13`, `ATM-G14`)
whose control *is* the sabotage and which carry it inside the test. One
(`ATM-G01`) is `unavailable`: the four operator keys were reordered in the
configuration and the served order did not move, because `CATEGORY_ORDER`
decides it — the forbidden state is not expressible by a deployment, and the
guard is named in the record rather than left as an assertion.

**Two sabotages left their gate green on the first attempt** and both were
defects in the proof machinery rather than in the product (`ATM-F-07`,
`ATM-F-08`). Both are recorded with what actually reddens the gate.
