# Debt-Completeness Ruling Evidence — measured costs for Q-A to Q-E

**This document is evidence, not a proposal.** It costs the options already in
front of Dave — `D-IMPL-117`'s fixed-vs-declared fork, `D-IMPL-112`'s three named
gaps, and the two sub-questions the spike surfaced — and it adds nothing new to
decide. **No option here is recommended, ranked, defaulted or preferred**; the
document deliberately declines to do that, and the only sentence in it containing
that word is this one.

Every figure below was **measured against this tree** at `85437a4`
(`docs(15.6): mark phase 15.6 executing in STATE.md`), by
`tests/spikes/test_debt_evidence_placement_cost.py`. Nothing here is a grep
estimate, a projection, or an inference from a docstring. Where a cost could not
be measured, the cell says so and names why; **no cell is blank**.

**Measured:** 2026-08-12. **Plan:** `15.6-01`.

---

## How to read the MEASURED COST column

| Marker | Meaning |
|---|---|
| a number | counted by AST walk, or read off an executed run |
| a hash | an observed `content_hash` of a stand-in the spike module owns |
| **executed** | the outcome of actually running the thing, not of reasoning about it |
| **NOT EXERCISABLE** | the surface the cost would land on does not exist yet; the cell names what would have to exist first |

**Call-site counts are AST call-site counts, not `grep -rl` file counts.** A
module that constructs the same type nine times is nine repair sites. The walk
covers `src/`, `runtime/`, `tests/`, `perf/`, `examples/` and `tools/`, excluding
`.venv`, `__pycache__` and `tests/spikes/` — the instrument does not count
itself.

**The baseline every Q-A address is quoted against** is the spike's stand-in
vessel carrying a plain `DebtAssessment` and nothing else:

```
f4cd0517db51dd66946af8b39c4b444f134884fc40b0ba2a77b69bcddc180105
```

---

## Q-A — Fixed field on the vessel, or declared content in the payload?

This is `D-IMPL-117`'s primary question. Four placements, each priced by an
**executed round trip** rather than by argument: build the product under the
placement, build the dimension-5 record beside it, and rebuild the product from
`(record, projection)` alone using the shipped rehydrator's own one-liner.

**These four rows are properties of the placement _shape_ applied to a member of
`ContextProductContract`, not of any one gap's field.** They therefore price all
three Track B vessel-carried members identically — plan `15.6-06`'s debt-evidence
carrier, plan `15.6-07`'s source-refresh recency slot and plan `15.6-08`'s
assessment-side obligation member. A ruling made on this table governs all three;
it is not scoped to the evidence carrier alone.

| Placement | Content address | Reconstructible from `(record, projection)`? | MEASURED COST | What a deployment is forced to carry |
|---|---|---|---|---|
| **1. Nested inside `DebtAssessment`** — an optional member of the assessment that already rides `ContentGenerationPath.debt` | **moves**, `f4cd0517…` → `7c32baeb…` | **YES.** Rebuilt bytes are byte-identical to the delivered bytes | **executed.** The evidence token is present in the canonical bytes of the record; the rebuild reproduces the address exactly. **0** rehydrator implementations change — the shipped `debt=record.content_generation_path.debt` carries a reshaped assessment verbatim | one optional member on a type every product already carries; the sentinel says what an unpopulated slot asserts |
| **2. New top-level field on `ContextProductContract`**, sibling to `debt` | **moves**, `f4cd0517…` → `e358be39…` | **NO.** Rebuild hashes to `84799e67…`, which is neither the delivered address nor the baseline | **executed.** The token is **absent** from the canonical bytes of both inputs. `ProjectionOutput` carries exactly `(plan_id, payload)` and dimension 5 carries no member naming the value, so no implementation of the `(record, projection)` signature can produce it. That is the `ReplayDivergence` raise path | a matching member on `ContentGenerationPath` **plus** an edit to every shipped `rehydrate_product` — otherwise every replay of every product raises |
| **3. Declared content inside `payload`**, under the shipped `payload_schema_key` / `payload_schema_version` shape | **moves**, `f4cd0517…` → `fecd33a2…` | **YES.** `payload` comes back verbatim on `ProjectionOutput.payload` | **executed.** Rebuild reproduces the address exactly, and the token is present in the projection bytes. **But replay never compares the evidence against the declared schema** — the conformity comparison lives at bind, on a seam `D-IMPL-113` ruled the SDK will not call | a registered payload schema per class; and the conformity check is the adopter's to place |
| **4. On the replay record only** — a new member of `ContentGenerationPath` | **does not move.** Address stays `f4cd0517…` | **YES**, trivially — there is nothing on the product to reconstruct | **executed.** The delivered bytes are what they are today. See Q-B for what this placement reaches | nothing on the product — and nothing reaches a wire consumer |

### Where `D-IMPL-97` draws the line, and where the two halves of a carrier fall

`D-IMPL-97` ruling 1 puts **cross-cutting governance in fixed structure** and
**domain content in a declared schema** the class registers, *"in the shape MCP
tools declare `inputSchema`"*. Its decisive argument for putting debt in fixed
structure was **debt by construction**: *"debt on the base vessel means every
product carries it while every subclass is a place to forget, and debt computed
and discarded is exactly the defect this review found."*

A debt-evidence carrier has two halves and they fall on opposite sides of that
line:

- **The pointer mechanism** — that evidence exists, that it is typed, that
  replay can reason over it and the address covers it — is the kind of thing
  `D-IMPL-97` calls fixed structure.
- **The pointer contents** — *which* observations are worth naming — is exactly
  the creator judgement `D-IMPL-117` assigns away from the SDK: *"the context
  product creator will have an idea of what is needed by the client."*

**This document does not choose.** The measured facts are that placement 1 and
placement 3 both round-trip; that placement 1 costs zero rehydrator edits and
placement 3 costs a registered schema plus an unenforced check; that placement 2
does not round-trip at all without new record-side structure; and that placement
4 round-trips and reaches nobody.

### What the real tripwire did when run

`tests/replay/test_engine_rehydration.py`, executed in a separate interpreter:
**exit 0, 24 passed.** Which placements that run exercises, and why the other two
cannot be exercised without a source change this plan is forbidden to make:

| Placement | Exercised against the real tripwire? |
|---|---|
| 1. nested | **NOT EXERCISABLE end to end.** `DebtAssessment` is frozen and `extra=forbid`, so an evidence member cannot exist on the shipped type without editing `src/ccf/halflife/assessment.py`. The round trip is instead executed above against a stand-in subclass carried through the **real** `ContentGenerationPath.debt` field, which is the load-bearing half of the claim |
| 2. top-level | **NOT EXERCISABLE end to end.** Requires a new vessel field, a new dimension-5 member, and a `rehydrate_product` that reads it back — three source changes |
| 3. declared | **exercised.** `payload` is already an open `Mapping`, so a payload carrying declared evidence needs no source change and the tripwire runs exactly as it does today |
| 4. record-only | **exercised.** The product's bytes are unchanged, so the tripwire runs unchanged and its result is the measured baseline |

---

## Q-B — Can the evidence ride the replay record rather than the product?

**Measured and rejected.** Not by argument — by an enumeration of every shipped
door, read off the source and asserted in the spike module so the finding cannot
rot silently.

| Door | Serializes | Reads `ServedProduct.replay_ref`? | MEASURED COST of a record-only carrier |
|---|---|---|---|
| `runtime/ccf_runtime/mcp/egress.py::build_egress_server` | `servable.product` | **no** | reaches **0** wire consumers |
| `runtime/ccf_runtime/http_api/routes/product.py::build_router` | `servable.product` | **no** | reaches **0** wire consumers |
| `runtime/ccf_runtime/mcp/experience.py::build_experience_server` | `servable.product` | **no** | reaches **0** wire consumers |

`ServedProduct` declares exactly two fields, `product` and `replay_ref`. Every
door serializes the first and none reads the second. The enumeration is the one
`tests/invariants/test_mcp_role_separation.py` holds as **exhaustive** over
runtime's product-serving handlers, so a fourth door fails that suite rather than
quietly widening this table.

**In-process reach, reported rather than asserted:** **19** bare-name `serve(`
call sites across **12** files — 10 in `tests/`, 9 in `examples/`, **0** in
`src/` or `runtime/`. That is the whole population that would see a record-only
carrier, and every one of them is a test or an example.

**And `D-IMPL-117` independently removed the reason to want it.** The only thing
placement 4 buys is avoiding the content-address move, and the address move is
now an authorized cost: *"`D-IMPL-116`'s framing of the spike as a way to avoid
the address move is superseded."* The saving has no buyer, and the reach is zero.

This is the option the spike exists to delete from the decision space for free.
It is recorded here as **deleted by measurement, not by argument.**

---

## Q-B2 — Does an evidence pointer leak entitlement? *(new, unruled)*

`D-IMPL-105` ruled the analogous question for **completeness**, and ruled it
precisely because of an inference channel: under a per-principal reading *"a
caller can therefore infer what they are not allowed to see from the debt they
are shown — an oracle over the entitlement configuration, quieter than a refusal
because nothing in the response says a consultation was declined."*

**No shipped ruling covers evidence pointers.** This is a new `D-IMPL` entry Dave
owes. Three measurements, each read off the shipped call chain. **No mitigation
is offered and no verdict is reached here.**

### Measurement 1 — is the enumerated view perspective-scoped or tenant-scoped?

**Tenant-scoped, then narrowed by operator parameters. Not principal-scoped.**
The chain, hop by hop:

| Hop | `path::Symbol` | What it does with the principal |
|---|---|---|
| 1 | `runtime/ccf_runtime/mcp/egress.py::build_egress_server` | calls `entitled_perspective` with the verified grant, binds the result, passes it to the deployment's resolver |
| 2 | `runtime/ccf_runtime/authz/product_entitlement.py::entitled_perspective` | resolves a `Perspective` from the grant, refuses a subject conflict, authorizes the `(tenant, product_class, role)` triple |
| 3 | `examples/s1-01-hello-context-product/spine.py::assemble_and_serve` | reads the graph as `reader.as_of(tenant_id=…, at=…)` — **tenant and instant, no principal** |
| 4 | `src/ccf/deployment/operators.py::build_operator_registry` | parameters are `(parameters, view, pins, policy_bundle_key, similarity_index_version)` — **no perspective, no principal** |
| 5 | `src/ccf/operators/categories.py::PolicyFilter` | constructor parameters are `(self, parameters)`; its admission test reads the entity record's policy-bundle version and a per-class classification attribute against **deployment-declared** values |
| 6 | `src/ccf/projection/engine.py::ProjectionEngine` | `execute` parameters are `(self, plan, perspective, tenant_id, temporal_boundary, seeds, recorded_acquisitions)`; the perspective is threaded into the **plan invocation** and nowhere else |
| 7 | `examples/s1-01-hello-context-product/deployment.py::KycScenario` | enumerates `view.entities` — the **post-operator** view — to build the `Observation` sequence the freshness scorer consumes |

Measured: `perspective` appears in `ProjectionEngine.execute`'s parameters and in
**neither** `build_operator_registry`'s nor `PolicyFilter.__init__`'s.

### Measurement 2 — would two differently-entitled principals enumerate the same `entity_uri` set?

**Yes, as the shipped path stands.** The operator stage that produces the
enumerated view takes no perspective, so two principals entitled to the same
product class are handed the same view.

- **Paths converge at** `src/ccf/projection/engine.py::ProjectionEngine` — the
  operator chain, which computes the surviving view without a principal.
- **Paths diverge at** `src/ccf/projection/plan.py::ProjectionPlan` — the plan
  invocation, which is the first and only stage the perspective reaches.

Entitlement is decided **before** assembly, at `entitled_perspective`, on the
`(tenant, product_class, role)` triple. That is a per-class decision, not a
per-entity one.

### Measurement 3 — what would a full-graph pointer expose that a scoped pointer would not?

**On the shipped path the two are the same set, so the delta is empty — and that
is the finding.** There is no perspective-scoped view to derive a narrower
pointer from. The narrowing that does happen is
`src/ccf/operators/categories.py::PolicyFilter`'s, keyed on permitted
policy-bundle versions and permitted classifications declared per deployment,
identically for every principal of the class.

The fields a pointer derived from `view.entities` could name are `EntityClaim`'s
eight: `tenant_id`, `observed_at`, `valid_from`, `valid_to`, `lineage`,
`entity_uri`, `entity_class`, `attributes`.

**Offered without mitigation and without a verdict.** The Wave-2 checkpoint puts
this to Dave as a new `D-IMPL` entry.

---

## Q-C — Required or optional on `Observation`?

**Executed, not inferred.** Each of the three named artifacts' *actual*
observation mapping was `model_validate`d against a stand-in carrying a required
identity field and again against one carrying an optional field behind a positive
sentinel, and what each raised was recorded.

`Observation` today carries exactly two fields: `observation_type`,
`observed_at`.

| Option | MEASURED COST |
|---|---|
| **Required identity field** | **6 code files** (10 `Observation(…)` call sites across 3 files — 9 in `tests/`, 1 in `examples/` — plus 3 `Observation.model_validate` sites in 3 example `run.py` files) **plus all 3 YAML artifacts**, each of which **raises** |
| **Optional identity field behind a positive sentinel** | **3 code files** (the 10 construction sites, which populate it) and **0 artifacts** — every artifact validates and the sentinel is carried |

**The three artifacts a required field breaks, named by full path, with what was
actually raised:**

| Artifact | Observation mappings | Under a **required** field | Under an **optional** field |
|---|---|---|---|
| `examples/00-quickstart/artifacts/decision.yaml` | 1 | `ValidationError`, 1 error, type `missing`, loc `subject_uri` | validates; sentinel carried |
| `examples/01-agent-basics/artifacts/debt-evaluation.yaml` | 2 | `ValidationError` on both, type `missing`, loc `subject_uri` | validates; sentinel carried |
| `examples/08-e2e-demo/artifacts/decision.yaml` | 1 | `ValidationError`, 1 error, type `missing`, loc `subject_uri` | validates; sentinel carried |

`15.6-RESEARCH.md` assumption A7 — *"the 3 example artifacts break only under a
required field"* — is **discharged by execution**, not by inference from
`extra=forbid` semantics.

**The governance trade, stated in both directions and not resolved.**
`D-IMPL-97`'s *"every subclass is a place to forget"* argument cuts toward
**required**: an identity nobody is obliged to supply is an identity some
assembler will omit, and the join key would then exist on the type and not in the
data. `D-IMPL-38`'s no-silent-defaults discipline, together with the shipped
positive-sentinel precedent (`NO_SCORER_PINS`, `NO_GRAPH_QUERIES`,
`NO_PAYLOAD_SCHEMA`), makes **optional** expressible without ambiguity: an
unpopulated identity would be a named positive assertion rather than a silence,
so an omitted identity and a dropped one would not be the same artifact.

---

## Q-D — Where the join key already is

**Gap 1 is a wiring change at the call site plus one field on the type. It is not
a build.**

At `examples/s1-01-hello-context-product/deployment.py::KycScenario`, the
assembler holds the whole `EntityClaim` in the loop variable, reads two of its
fields, and drops the rest.

| Fields in hand on `record.claim` | Fields carried into `Observation` |
|---|---|
| `tenant_id`, `observed_at`, `valid_from`, `valid_to`, `lineage`, `entity_uri`, `entity_class`, `attributes` | `observation_type` (from `entity_class`), `observed_at` |

**Available and discarded: 7 fields** — `attributes`, `entity_class`,
`entity_uri`, `lineage`, `tenant_id`, `valid_from`, `valid_to`. Each
`LineageEntry` inside `lineage` additionally carries `source`, `envelope_id`,
`observed_at` and `passage_anchor`.

**The consequence, stated plainly.** `D-IMPL-99` ruled per-subject and per-claim
attribution NOT MEASURABLE because *"there is no structure in this tree to count
a per-subject cost against."* That was true of the **type** — `Observation`
carries no identity — and it was **never true of the call site**, where both the
canonical entity URI and the full per-claim provenance are in scope and thrown
away. Gap 1 is *"stop discarding the join key"*, not *"build one"*.

Measured and reported alongside: `Observation(…)` still has **0** construction
sites in `src/` or `runtime/`. The SDK ships the type and never constructs one,
which is why an added field costs the SDK itself nothing.

---

## Q-E — The regeneration surface, re-derived at this base

The census was re-run over `src/ runtime/ tests/ examples/ tools/ perf/ docs/
public/` at this plan's own base commit rather than carried from
`15.6-RESEARCH.md`.

| Figure | Measured |
|---|---|
| Files holding address literals | **18** |
| Full-length 64-hex literals | **123** across 17 files |
| Truncated (elided) address literals | **2** in 1 file |
| Files that **move** when `DebtAssessment` reshapes | **1** |
| Unclassified files | **0** |
| Drift against the research figure of 1 | **0** |

**The count matches the research. The mechanism does not, and that is the
finding.**

A 64-hex sweep over these trees finds **zero** literals in
`examples/08-e2e-demo/artifacts/expected_output.txt` — the one file
`15.6-RESEARCH.md` § B1 and `D-IMPL-116` both name as moving. The reason is that
the example prints its addresses **elided to a 16-hex prefix followed by `...`**,
a form a full-length sweep is blind to. A census without the truncated pattern
would have reported a *smaller* regeneration surface than the tree has.

The second half of the finding is **what that file actually pins**: not the
product content address, but the **replay-record address** and the
**skill-set-in-force hash**. Both still move on a `DebtAssessment` reshape — the
replay record carries `ContentGenerationPath`, which carries `debt` — so the
count of one holds. But a planner budgeting for *"regenerate the product address
in one example artifact"* would be budgeting against the wrong mechanism.

Every other hit is classified as **does not move**, with its reason:

| File | Literals | Reason |
|---|---|---|
| `tests/replay/test_harness_trace.py` | 1 | self-normalizing — a freshly computed `content_hash` is substituted for the captured literal before comparing |
| `tests/replay/test_engine_rehydration.py` | 6 | computed, not pinned — compared against a live `content_hash(outcome.product)` |
| `examples/external/00-hello-context/.store/…` | 1 | gitignored store index; regenerates on every run |
| `examples/external/00-hello-context/fixtures/…` | 5 | recorded LLM request bodies; the replay server fingerprints model, sorted tool names and message count, never message content |
| `examples/08-e2e-demo/artifacts/scenario.yaml` | 4 | source fingerprints and a ring signature, not product addresses |
| `tests/peering/test_admission_record.py` | 1 | a sha256 of the `claims.py` file text; moves only if `claims.py` is edited, which no Track B gap requires |
| `tests/authz/test_authz_audit.py` | 1 | canonical bytes of an `AuditEvent`, which carries no product |
| `tests/test_surface_completeness.py` | 1 | a digest of the frozen v0.2 surface baseline, frozen by design |
| `tests/perf_synth/…` | — | synthetic dataset hashes, unrelated to any product |
| `tools/lints/allowlist.yaml` | 3 | CINV-01 finding fingerprints over literal text |
| `tools/lints/tests/test_no_hardcoding.py` | 1 | a CINV-01 allowlist fingerprint; no product involved |
| `docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md` | 1 | the `15.5-01` evidence document — a historical measurement of a stand-in, not a live pin |
| `docs/DECISIONS.md` | 2 | append-only ruling record; quoted measurements, never re-derived |
| `docs/PHASE_I4_GATE.md` | 1 | a transcript of a past failing test run |
| `docs/SURFACE-AUDIT.md` | 1 | a sha256 of the committed surface baseline, quoted as a historical record |

---

## Already ruled — not questions

A ruling package that re-opens a standing ruling wastes the one thing this
checkpoint spends. These are settled and are **not** on the table:

- **`D-IMPL-117` — surface impact is accepted.** The `Observation` identity
  field, the `DebtAssessment` evidence pointers and the third
  product-content-address move are **authorized costs, not risks to design
  around**. The address move is not a reason to prefer one placement over
  another, and Q-A's four rows are not a cost-avoidance table. Do not
  re-litigate it.
- **`D-IMPL-116` — the two tracks, planned separately.** Track A is API-neutral;
  Track B carries every API change. Track B is scoped to `D-IMPL-112`'s three
  named gaps, **not** to the open question *"would someone act on this?"*.
- **`D-IMPL-101` — salience is deferred; recency ships, salience does not.** No
  salience mechanism lands in this phase, and the two shapes a later cycle may
  choose between are recorded there rather than anticipated here.
- **`D-IMPL-113` — bind-time payload conformity is an adopter obligation.** The
  SDK ships `refuse_bound_payload` and does not call it. This is why placement 3
  in Q-A sits behind a gate the SDK has ruled it will not enforce: a declared
  payload schema disciplines the payload only where an adopter's own resolver
  chooses to run the comparison.

---

## Provenance

Every figure in this document came from
`tests/spikes/test_debt_evidence_placement_cost.py`, run at `85437a4`. The
module obeys one rule, stated in its own docstring: **assert only facts that no
plan in this phase is scoped to change; report everything else.**

**Asserted** — and therefore held green by `make ci-core` for the rest of the
phase — are the four Q-A placement verdicts (properties of `content_hash` over
stand-in models the module owns), the Q-B three-door enumeration (no plan in this
phase touches `runtime/`), the Q-D limb that `EntityClaim` declares `entity_uri`
and `lineage` (pinned by the `claims.py` file hash in
`tests/peering/test_admission_record.py`), and that the stand-in observation
models behave as stand-ins.

**Reported, never asserted** — because plans `15.6-05`, `15.6-06`, `15.6-07`,
`15.6-08`, `15.6-10` and `15.6-11` each move what they count — are the Q-C
censuses and the executed artifact breakage, the Q-D fields-in-hand comparison,
the Q-E regeneration census, the Q-B in-process reach, the three Q-B2 entitlement
findings, and the tripwire outcome. A module asserting any of those would go red
on *correct* work by a later plan in its own phase, and the only available repair
would be to edit the evidence. Editing the evidence to keep a gate green is the
opposite of evidence.

The one exception on the reported side is an instrument check: the AST walk
asserts that it *found* each symbol at all. A walk returning zero for
`DebtAssessment` means the walker is broken, which is a fact about the instrument
rather than about the tree.

**Retiring owner: plan `15.6-12`, task 1.** The module is a measurement
instrument with a phase-length life. `15.6-12`'s phase-close sweep either retires
it or re-points it at the post-ruling tree, and accounts for the choice in the
gate package. No other plan owns it.

**How to re-run the measurements:**

```
CCF_SPIKE_REPORT=/tmp/figures.json \
  .venv/bin/python -m pytest tests/spikes/test_debt_evidence_placement_cost.py -q
```

Every source citation in this document is in `path::Symbol` form. That is
deliberate: this is the phase that fixes citation rot, and a findings document
written in `path:line` form would be its own exhibit A.
