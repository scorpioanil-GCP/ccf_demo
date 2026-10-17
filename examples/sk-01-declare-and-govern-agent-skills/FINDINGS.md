<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# sk-01 · declare and govern agent skills — findings

**Scope of this record.** The skills example built under Dave's ruling of
2026-10-16 16:58 MST (option A), recorded in `docs/DECISIONS.md` under "sk-01 —
the skills example, option A RULED 2026-10-16 16:58 MST". Dave, verbatim:
*"Gaps 1, 3 and 4, and the new findings F-01 through F-04, stay recorded and
parked. The three-issue cap is already exceeded; do not start additional SDK
work for the example."* So every finding below is **PARKED** (Dave, 2026-10-16
16:58): recorded, classified as proposed, and not worked on. Nothing in `src/`
or `runtime/` was changed for this example. Each finding was classified under
`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before anything was changed; the
categories are proposals for Dave, not rulings.

**What was and was not measured.** 192.168.4.76 was not contacted while this
example was built or reviewed. It was read afterwards, read-only, on 2026-10-16
(`fibo-v2` and `ccf_v2`, with cp-06-canonical's door started locally from branch
`replay-evidence-383`): the estate tests (E1–E5 in
`tests/examples/test_sk_01_estate.py`) **passed on their first run**, and
`run.py` was run three ways (the demonstration question and the README's two
variations). Anything not labeled *"on the estate"* below was measured
estate-free, by a test in this repository unless it is labeled otherwise. A claim labeled
*"out-of-tree probe"* was measured on 2026-10-16 by an estate-free probe that is
not committed and cannot be reproduced from this repository; it is kept as
provenance, not as evidence an examiner can rerun.

## 1 · SDK capability proven (§D)

Only what a gate in this repository, or a recorded measurement, shows.

| §D item | status here | evidence |
| --- | --- | --- |
| **acquire … by governed grant** | **Shown.** The grant is requested and put in force at open, and only the declared grant is. On the estate, the admitted child row carries the grant the audit log recorded effective for its skill. | `test_o2_…`, `test_o2b_…` (`tests/examples/test_sk_01_offline.py`); E2 on the estate |
| **apply authorization and policy before use** | **Shown at open.** The over-reaching grant is refused by tier 1 before anything is composed, by name, with the excess scope, and audited (`grant_requested`, then `grant_refused`). | `test_o1_…` |
| **refuse correctly** | **Exercised with findings, not proven.** A question outside the temporal boundary is refused as data (`RefusalEnvelope`, `asked-at-outside-temporal-bound`) with a record. On the estate, the expired-evidence facility is refused `composite-child-refusal`, the child row `ineligible` with the producer's `ttl-refusal` / `ttl-bounds`. A refused *open* raises `DeclaredGrantRefused` and leaves no replay record (SK01-F-04). | `test_o6_…`; E3 on the estate; `test_o1_…` |
| **preserve sufficient refusal evidence** | **Exercised with findings, not proven.** A refused question's record names the agent and its skill-set, on the estate too. A child row that was not admitted omits the skill and grant: measured on the estate for the `ineligible` row, which does carry the producer's refusal kind and reason (see "Observed while building"). | `test_o6_…`; E3 on the estate; the live `run.py` output |
| **compose; local and remote boundaries** | **Exercised on the estate.** The brief admitted cp-06-canonical's product from that producer's own door in another process, and the child row names the producer registration. | E2 on the estate; the live `run.py` output |
| **replay and reconstruct; tenant/product/provider identity** | **Not measured in this build.** Composite replay through `replay_decision` is gap 3, parked. | — |

**Dimension 4 names the composing agent (`D-IMPL-385`), bound by this example.**
`test_o6_a_refused_decision_names_the_declared_agent_and_its_audited_skill_set`
asks a question the temporal boundary refuses before any leg is read and holds
the record to the declared agent (content hash, versioned URI, archetypes) and to
the skill-set of the grants audited effective at open. **Severed** on a scratch
copy of the tree (2026-10-16; `agent=agent` removed from the paved resolver's
construction in `src/ccf/products/product.py::_derive_consumer_chain`; file
restored from saved bytes, sha256 `819ff24f…` checked, `__pycache__` purged,
`python -B`): O6 went red on its assertion, `'no-agent' == '13b2a606…'`, and
green again after the restore. The SDK-level gate is
`tests/products/test_dimension_four_records_the_agent.py`.

## 2 · SDK friction observed (§E)

**The target chain** — *requires → skill grant → producer registration →
argument mapping → governed child* — is met on the skill-chain half, and departed
from in what surrounds it.

**(a) Skill-chain configuration: five declarations, agreeing by construction.**
`policy.skill_governance`, `producers`, `skills`, `agent`, `grants`. The SDK
derives the catalog entry from `skills:`, requests each `grants:` entry through
the ledger, and refuses at open, by name: an over-reach (`test_o1_…`), a
`skills:` entry `grants:` does not name (`test_o2b_…`, `GrantNotInForce`), and a
stated non-product type (`test_o3_…`). This is the chain working as intended.

**(b) Glue every adopter would rewrite (SK01-F-02).** `tool_surface.py` lines
88–101, **12 code lines**: a second `GrantLedger` and `SkillCatalog` over the
same Control Plane, and an `AgentFactory` construction keyed by
`opened.keys.agent` and the content-hash version rule.

**(c) An audit-log grant reader.** `AuditLog.events()`
(`src/ccf/controlplane/audit.py::AuditLog`) takes no filter by action, so the
example filters it itself: `run.py`'s `GRANT_ACTION_PREFIX`, `_short`,
`_grant_events` and `_print_grant_events`, **11 code lines**. Two more copies
live in the tests (`test_sk_01_offline.py::_grant_events`,
`test_sk_01_estate.py::_effective`). Before this review round `run.py` spelled
the four actions as a tuple that omitted `grant_pending_approval`; it now follows
the `grant_*` family `audit.py` documents. Harmless here either way, because
`grant_requires_approval` is false.

**(d) SDK-internal knowledge the record checks depend on.**

- A grant audit event's `version` is the grant's content hash. That is stated
  only inside the private `GrantLedger._put_state`
  (`version=content_hash(grant)`); the public field says *"The version
  involved"*.
- The record's skill-set equals `grant_set_hash` over the effective grant hashes
  only while at least one grant is in force; otherwise
  `GrantLedger.grant_set_hash` returns the `no-grants` claim.
- The grant's Control Plane key is `{tenant}/ccf.skill-grant/{name}`. The public
  `src/ccf/skills/grants.py::skill_grant_key` derives it, but only from a
  `SkillGrant` the example never holds, so `run.py` rebuilds it from
  `SKILL_GRANT.class_id`.
- **Size, measured** (Appendix-A counter of `docs/PAVED-ROAD-LOC-REPORT.md`):
  the record-join part of `run.py::movement_two` (from the `effective` mapping to
  its return) is **38 code lines**, and `run.py::child_rows_held` is **26**, both
  including their prints. The design estimated "about 4".

**(e) Duplicated configuration authorities.** One name stated in places that can
disagree.

*Restated, and NOT checked against each other by the SDK:*

- **The identity attribute names** (`lei`, `legal_name`, `legal_jurisdiction`),
  in five places: `artifacts/source-vocabulary.yaml` lines 26–29,
  `ccf_config.yaml` lines 95–97 (`resolution.entity_rules[].attribute_keys`),
  `acquisition.py` lines 93–96, `deployment.py` lines 110–112, and
  `projection.py` line 97.
- **The match key** `obligor_ref`: `ccf_config.yaml` line 91 and
  `deployment.py` line 73.
- **The product name**: `ccf_config.yaml` line 36 and the `plan_id` prefix,
  `deployment.py` line 77.
- **The child class** at `artifacts/projection.yaml` line 24, guarded only by
  `deployment.questions`, which raises a `ValueError` when the mapping is called
  during the answer.
- **The obligor class** at `artifacts/projection.yaml` line 20, and as the
  half-life key at `ccf_config.yaml` line 110.
- **The facility parameter name** at `artifacts/question.yaml` line 39, against
  `ccf_config.yaml` line 79.
- **The source label** `SOURCE = "identity"` at `deployment.py` line 62,
  against `ccf_environment.yaml` line 27.

*Restated, and checked by the SDK at open, by name* — counted as restatements,
not drift risks: the child class at `ccf_config.yaml` lines 61, 165 and 223, and
the obligor class at lines 66 and 92.

*How the unchecked copies fail when they drift* (read in code; the
measurements were made by review round 1's out-of-tree probes):

- A column renamed in `source-vocabulary.yaml` fails **loudly**: `KeyError` in
  `acquisition.resolve`.
- A match key that drifts between `ccf_config.yaml` and `deployment.py` fails
  **silently**: `src/ccf/assembly/worker.py::SpecDrivenEntityResolution`
  skips a rule whose match key is absent from the payload, so no entity
  resolves, nothing raises, and the brief refuses on its empty own view without
  naming the drift.
- An attribute key renamed in `ccf_config.yaml` fails **silently**: the same
  resolution keeps only declared keys present in the payload, so the attribute
  is dropped, and Π prints the declared `NOT_EVALUABLE` (before this round it
  printed an empty string).

*Cause on the SDK side:* `AcquisitionContext` does not carry the resolution
spec, so an `acquire` cannot read the match key or the attribute keys it must
write. *Repetition:* cp-14 restates the same kind of names (its
`acquisition.py` and `deployment.py`); under §E repeated friction is evidence.
*Proposed category:* §B.2 candidate ("a value that must be stated in two
authorities that can drift apart"), **parked** under the 2026-10-16 ruling; no
SDK work started.

**(f) The variant.** A whole second deployment (two documents,
`variants/over-reach/`) to change one skill block; `test_o4_…` holds the copy
equal.

**(g) Product scaffolding to host one grant (SK01-F-05).** Measured below.

**(h) Failure timing.** Every skill-chain mistake above is refused at open, by
name — the good case. The one ordering rule (SK01-F-02) surfaces as an
`AgentDefinitionError` about an unregistered debt-profile reference, which does
not say "ask a question first".

## 3 · Launch blockers

**None ruled.** SK01-F-01 carries a candidate §C step-1 *"No"* (§D lists "local
callables … by governed grant", and no example can grant one); it is a
**proposal**, and Dave's ruling parks it. No finding here has a decision id
making it a blocker.

## 4 · Backlog candidates (§I)

The parked findings, each recorded in full below:

| id | finding | proposed category | status |
| --- | --- | --- | --- |
| SK01-F-01 | the supported path cannot declare or grant a harness-exposable skill | candidate §B.1 | PARKED |
| SK01-F-02 | the paved agent's tool surface needs SDK-internal knowledge | candidate §B.2 | PARKED |
| SK01-F-03 | a skill's requirements are not pinned in the decision record (unsure) | for Dave | PARKED |
| SK01-F-04 | grant audit lives only in memory (unsure) | for Dave | PARKED |
| SK01-F-05 | the product scaffolding an agent needs to hold one grant | evidence for gap 4 | PARKED with gap 4 |
| §2 (e) | duplicated configuration authorities | candidate §B.2 | proposed; parked by the ruling |

Gaps 1 (a run-time grant/revoke door), 3 (composite replay through
`replay_decision`) and 4 (an agent outside a product) stay parked (`D-IMPL-385`
and the sk-01 ruling).

## 5 · Estate / example limitations

- **The estate was read once, after the build** (2026-10-16, read-only). The
  cp-06-canonical door **admitted** the demonstration child (BGC Group,
  `FAC-5B8418`), as cp-14 measured on 2026-10-11, and refused `FAC-D3D1A4`
  `ttl-refusal` / `ttl-bounds`, as cp-06-canonical's own gate expects
  (`D-IMPL-341`, `tests/examples/test_cp_06_canonical_output.py`). Both depend on
  the snapshot estate and the pinned instant (§B.4).
- **The illustrative calibrations** — the one-hour `temporal_boundary`, the
  `demonstration_serve_instant`, the brief's own `half_life` and `debt_profile`,
  and the pinned asked-at instant — are disclosed where they are declared and in
  the README.
- **Scopes are labels.** Nothing here enforces "read" against "write"; tier 1
  compares labels (README).

## 6 · Product result

**Against the estate (2026-10-16, read-only; no transcript is published, README
only):**

- the demonstration question (BGC Group, `FAC-5B8418`, 2026-09-07T12:00Z) was
  **served**, with cp-06-canonical's collateral section admitted: commitment
  40,000,000, coverage ratio about 5.50, shortfall 0;
- the expired-evidence facility (`FAC-D3D1A4`) was **refused**
  `composite-child-refusal`, its child row `ineligible` with `ttl-refusal` /
  `ttl-bounds`;
- the question asked outside the one-hour boundary was **refused**
  `asked-at-outside-temporal-bound` before any child was asked;
- in all three, dimension 4 named `collateral-analyst` and the same skill-set
  hash, and `run.py` exited 0.

Estate-free, measured by the offline gates:

- the main deployment opens, and the one declared grant is requested and put in
  force (`grant_requested`, `grant_effective`, same grant hash);
- the over-reach variant refuses to open, `DeclaredGrantRefused`, check
  `tier-1-policy-compatibility`, excess `collateral-ledger.write`, and the audit
  log holds `grant_requested`, `grant_refused` for one grant hash;
- a question outside the temporal boundary is refused
  `asked-at-outside-temporal-bound`, and its record's dimension 4 names
  `collateral-analyst` and a skill-set that is the hash of the grant audited at
  open;
- the agent's tool list through the Claude Agent SDK adapter would be empty
  (SK01-F-01), but cannot even be built before the first question (SK01-F-02).

**What a consumer can rely on:** that this agent cannot open holding a skill its
regime does not permit, and that a decision's record names the agent and the
identity of its skill-set. **What it cannot rely on yet:** listing the skills
behind that identity from the record alone (SK01-F-03, SK01-F-04), or seeing a
granted skill as a model tool (SK01-F-01).

---

## SK01-F-01 — the supported path cannot declare or grant a harness-exposable skill

**Status: PARKED** (Dave, 2026-10-16 16:58). **Proposed category:** §B.1
candidate — §D lists "local callables … by governed grant", which suggests a §C
step-1 *"No"*. The classification is Dave's.

**Evidence.**

- The paved `skills:` derivation fixes every declared skill's type to
  `mcp_product` and refuses any other stated type, by its own words
  (`src/ccf/deployment/config.py::_PAVED_SKILL_TYPE`, `D-IMPL-343` R-7).
  In-tree: `tests/examples/test_sk_01_offline.py::test_o3_a_harness_exposable_skill_cannot_be_declared_on_the_paved_road`,
  over all three harness-exposable types; it is written to go red when this is
  fixed.
- `grants:` may name only `skills:` entries
  (`src/ccf/products/product.py::_request_declared_grants`); the derived
  resolver is handed an empty `CallableRegistry()`, and `open_product` takes no
  callable registry.
- **The second route is closed too.** `_PAVED_SKILL_TYPE`'s own comment names a
  tool-type skill declared in its own catalog document and handed to a
  composite through the low road's `children=` hatch. The hatch is refused
  beside a declared `agent:`/`skills:`
  (`src/ccf/products/product.py::_refuse_half_wired_composite`), so nothing on
  it requests a grant. `GrantLedger.request` accepts only the `skill.grant`
  door's capability, which no example can reach (gap 1), or the composition-time
  `DeclaredSkillGrant`, which the SDK mints only for `grants:` entries naming
  `skills:` entries — always `mcp_product`. A script could mint one (the lint
  that holds minting to composition roots does not scan `examples/`), but that
  would be a bypass; `test_o5_…` forbids it here. This is the evidence for the
  design's open question of whether F-01 folds into gap 1.
- Movement 3: the adapter's tool list for the granted agent is empty, which is
  the correct answer for an `mcp_product` skill (TP-03).

**Consequence.** CLAUDE.md §7.3 seam 2 cannot be demonstrated from an example:
it is *called* (movement 3), but neither half of its contract — a granted skill
surfaced as a tool, an ungranted one absent — can be shown. **And the
tool-surface gate E4 cannot be severed validly today.** The only bound skill is
`mcp_product`; widening the adapter's filter makes the tool-surface renderer
raise `src/ccf/skills/toolsurface.py::SkillHasNoToolSurface`, a severing that
errors and is therefore invalid by this project's rule. So E4 is a weak
`() == ()` gate. Its oracle is the SDK's own
`HARNESS_EXPOSABLE_SKILL_TYPES`, which the SDK pins at
`tests/skills/test_harness_exposable_roster.py`; E4 becomes meaningful only once
F-01 is resolved.

## SK01-F-02 — the paved agent's tool surface needs SDK-internal knowledge

**Status: PARKED** (Dave, 2026-10-16 16:58). **Proposed category:** §B.2
candidate — an unstated ordering rule. It repeats item 5 of the `D-IMPL-385`
feasibility probe (recorded under `D-IMPL-385` in `docs/DECISIONS.md`).

**Evidence.**

- `src/ccf/products/product.py::OpenedProduct` exposes the agent's
  *definition* (`opened.agent`) and its key (`opened.keys.agent`) but no
  constructed `Agent` and no grant ledger. Nothing in `src/` or `runtime/` calls
  `AgentFactory(` (grep, 2026-10-16: zero call sites).
- So `tool_surface.py` rebuilds what the SDK built at open: a second ledger and
  catalog over the same Control Plane, the `<tenant>/agent` key and the
  content-hash version rule — 12 code lines (§2 (b)).
- **The ordering rule, in-tree:**
  `test_o8_the_paved_agent_cannot_be_constructed_before_the_first_question`.
  Before the first question, the agent's pinned debt-profile reference resolves
  to nothing the Control Plane has registered, and the factory raises
  `AgentDefinitionError`. Movement 3 follows movement 2 for that reason. The
  test is written to go red when the rule is lifted.

## SK01-F-03 — a skill's requirements are not pinned in the decision record (unsure)

**Status: PARKED** (Dave, 2026-10-16 16:58). **Severity:** for Dave.

**Evidence.**

- A grant names its skill by `name@version`. Dimension 5 carries the skill's
  name and version and the producer registration's address
  (`src/ccf/replay/record.py::ChildResolution`), not the skill's
  `requirements`.
- *Out-of-tree probe* (2026-10-16, estate-free; not reproducible from this
  repository): dimension 2 pins the policy bundle, the request contract and the
  temporal boundary, but not the skill entry.
- *Out-of-tree probe* (same): two deployments whose skill differed only in its
  `requirements`, at the same version, produced the same grant hash — one grant
  effective, one refused. That is why the over-reach variant bumps the skill's
  version to 1.1.0, which `test_o4_…` asserts.

**Consequence.** An examiner cannot recheck the tier-1 decision from the record
alone.

## SK01-F-04 — grant audit lives only in memory (unsure)

**Status: PARKED** (Dave, 2026-10-16 16:58). **Severity:** for Dave.

**Evidence.**

- The audit log is in memory, and
  `src/ccf/controlplane/state.py::InMemoryStateStore` is the only Control Plane
  state store implementation in `src/` or `runtime/` (read, 2026-10-16).
- A refused declared grant makes no decision and no record: the open raises
  `DeclaredGrantRefused` before anything is composed (`test_o1_…`), and the
  refusal exists only in that process's audit log. Its evidence ends with the
  process.
- The same holds for the grants behind a served decision's skill-set hash:
  turning that hash back into skills needs grant artifacts that live only in the
  in-memory Control Plane.

## SK01-F-05 — the product scaffolding an agent needs to hold one grant

**Status: PARKED with gap 4** (Dave, 2026-10-16 16:58: *"Gaps 1, 3 and 4 … stay
recorded and parked"*). The approved design recorded F-05 as evidence for gap 4
(an agent outside a product), not as a new issue, which is why the ruling's list
of new findings stops at F-04.

**Evidence, measured 2026-10-16 on this tree.**

- **14 of `ccf_config.yaml`'s 19 top-level keys** lie outside the five
  skill-chain declarations (11 sections plus `semver`, `tenant_id` and
  `backend`; `policy` is counted with the chain because it carries
  `skill_governance`): **79 non-comment lines**.
- **188 code lines** by the `docs/PAVED-ROAD-LOC-REPORT.md` Appendix-A counter:
  the own leg's `acquire` and `assess` (with `_instant`) in `deployment.py`,
  **43**; Π (`projection.py`), **82**; the identity leg (`acquisition.py`),
  **47**; the plan factory (`produce.py`'s `BriefPlanFactory`), **16**.
- None of it is what this example is about: a paved product must have an own
  leg (an empty own view refuses), and an agent that holds grants exists only as
  a composite's composing agent (`src/ccf/products/product.py::_derive_consumer_chain`).

## Observed while building

- **A child row that was not admitted names no skill and no grant.** Measured on
  the estate (2026-10-16): the expired-evidence row — the producer was reached
  and refused `ttl-refusal` / `ttl-bounds` — is `ineligible` with no skill and no
  grant, though it carries the producer's refusal kind and reason. Dimension 4
  still carries the skill-set hash. A producer-unavailable row does the same: seen
  by the builder in an uncommitted, estate-free scratch run with the producer at
  `127.0.0.1:1`; no committed test reproduces either case. The row carried a
  `child_question_address` (the hash of the question as formed, computed before
  dispatch in `src/ccf/skills/dispatch.py::_invoke_mcp_product`). The dispatch
  was attempted, but the one connection was refused (its `unreachable` branch),
  so nothing reached a producer. The row names the producer registration and
  server but no skill and no grant, although the dispatch ran under the catalog
  entry (its failure carries `skill_name`): the refusal it is built from,
  `src/ccf/products/composite.py::ChildAdmissionRefusal`, has no skill or grant
  member. The SDK's own prose calls this case a question "sent"
  (`ChildResolution.child_question_address`) and a producer that "was reached"
  (`GrantBoundChildResolver`'s refusal detail). Recorded only; no SDK work
  (the issue cap is exceeded).
- **The child-row check failed a correct refusal.** A review-round edit made
  `run.py` print `NO` (exit 1) for any record without a row for the required
  class; the live outside-the-boundary run exposed it, because that refusal comes
  before any child is asked. Fixed in the example: a *served* brief must carry an
  admitted row; a refused one may carry none (`test_o7_…`, severed red and
  restored).
- **A null in the estate was coerced to an empty string** by this example's
  identity leg before this review round, which defeated the SDK's null-attribute
  omission (`D-IMPL-357` B4). Fixed in the example: the leg passes `None`
  through, and Π prints the declared `NOT_EVALUABLE`.
- **The estate tests could print the DSN.** Before this round a failure while
  asking would have rendered psycopg's connection arguments, password included.
  Fixed in `test_sk_01_estate.py` (the `asked` fixture). The same class stands
  in frozen estate tests — `tests/examples/test_cp_14_first_slice.py` and
  `test_cp_14_second_slice.py` — which are not changed here (`D-IMPL-261`).
- **The spawned door kept evidence on local disk.** It inherited
  `CCF_REPLAY_EVIDENCE_ROOT` from the operator's shell; `test_sk_01_estate.py`
  now strips it. The same one-line fix applies to
  `tests/examples/test_cp_14_third_slice.py` and
  `test_cp_06_canonical_output.py`, which need a ruling to change.
- **The DSN guidance.** The recipe's "Connection strings" paragraph
  (`public/reference/specifications/example_delivery.md`) says a DSN can be as
  short as `dbname=<database>`; such a DSN connects as whatever role `PGUSER`
  names. This example's README and environment remedy now say so; the recipe
  itself and the frozen specimens carrying the same text are unchanged. A
  client-side read-only session (`connection.read_only = True`) was not added:
  it touches the area of Dave's 2026-10-10 ruling on read-only enforcement and
  needs his confirmation first.
