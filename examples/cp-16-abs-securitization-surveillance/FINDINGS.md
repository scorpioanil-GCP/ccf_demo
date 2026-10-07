# CP-16 — ABS / Securitization Surveillance · FINDINGS

**Accepted at `D-GATE-cp-16`, 2026-09-21**, on the candidate `cp-16-abs @ 5915d959`,
merged `--no-ff` into `main`. **No SDK or runtime change.** 22 declared / 22
executing gates; 21 observed red under sabotage; 1 `unavailable` with its guard
named; 41 tests passed, 0 failed, 0 skipped; active issue cap 0 of 3.

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B **before remediation**,
as that policy requires. Every measurement was taken against the live estate on
**2026-09-21** with `CCF_REQUIRE_ESTATE=1`.

**Active SDK issue cap: 0 of 3.** No finding here is a new SDK gap. Two are the
SDK behaving correctly and refusing to guess; two are working-as-designed
friction notes; one is an existing backlog item gaining new evidence; one is
carried from a closed decision; four are defects in **my own proof machinery**,
corrected and recorded rather than quietly swapped; the rest are estate or
design consequences.

---

## 1 · SDK capability proven (§K.1)

| Launch-contract item (§D) | How this rung exercised it |
|---|---|
| define contracts as Control Plane artifacts | `cib.abs-surveillance` with a four-value `ArgumentDomain`, a role-applicable ceiling, 22 declared gates |
| apply authorization and policy **before use** | the granularity ceiling is formative at the acquisition seam — a loan row above it is never selected |
| refuse correctly, by name, as data | four distinct governed refusals: `not-in-allowed-set`, `granularity-not-in-domain`, `unbounded-loan-request`, `unpriced-intent` |
| preserve product identity and content addressing | `ABS-G21`: same question, same bytes; a different instant or role is a different address |
| calculate Context Debt per the declared λ_c | two observation types, `supersede-only` and `valid-from`, gated at `ABS-G19` |
| propagate lineage and expiry by the declared anchor | `from_entity_freshness` on the servicer report's period, gated at `ABS-G20` |
| replay and reconstruct from the record | `ABS-G21`, including the executed operator plan in dimension 5 |

---

## 2 · SDK friction observed (§K.2, measured per §E)

### `ABS-F-11` — a request property may not author its own `enum`
**Category 3 (backlog note). Working as designed.** Writing `enum:` beside a
property is refused (`extra_forbidden`); the domain is declared once in
`argument_domains` and the JSON-schema `enum` is **derived** from it by
`src/ccf/products/request_schema.py`. This is `D-IMPL-259` holding — the
parameter's valid domain has exactly one home — and the refusal is at boot, by
name, which is the good failure timing (§E). Recorded only because an adopter
writing JSON-schema by habit will meet it, and nothing on the public surface
says the two keys are not interchangeable.

### `ABS-F-12` — operator keys are the SDK's, not the deployment's
**Category 3 (backlog note). Working as designed.** Naming an operator
`policy.disclosable-subgraph` fails at resolution with `UnregisteredOperator`:
the four keys are fixed class attributes in `src/ccf/operators/categories.py`.
Correct — the key is mechanism, not a value — and the failure is loud. The cost
is one round trip for an adopter who expects to name their own.

### `ABS-F-06` — the bound reaches the examiner, not the caller
**Category 3, CARRIED from a closed decision. Ruled at `D-GATE-cp-16`: the
caller-facing minimal envelope may redact the reason while the governed
determination retains the actual bound — existing `D-IMPL-345` behavior, NOT an
HTTP defect to reopen.** Dave's ruling requires the
ceiling refusal to carry the bound. It does — `not-in-allowed-set`, the role,
the ceiling and the requested value are all present **in the replay record**,
verified by reading it back. The caller-facing envelope redacts `error_code` to
`"undisclosed"` under this deployment's `minimal` disclosure posture, so the two
governed refusals are observationally identical to a consumer. That posture is
the ladder's standing one (the `CP17-F` family, closed at `D-IMPL-345`, whose
`full` override was measurement-only and must never be persisted). **Not
reopened here**, and `ABS-G09` asserts against the determination rather than the
envelope.

### `ABS-F-13` — the block figure costs a second execution
**Category 4 (example limitation).** `blocks_scanned` is read by
`EXPLAIN (ANALYZE, BUFFERS)` on the same statement, which is how `ccf-dataprep`
measured the published curve — and explaining a statement **runs** it. So the
demonstration pays roughly twice for the leg it is measuring. Disclosed in the
README and in `acquisition.py`; a production deployment would sample rather than
measure every serve.

---

## 3 · Launch blockers (§K.3)

**None.** No finding on this rung is category 1 or a ruled category 2.

---

## 4 · Backlog candidates (§K.4)

### `ABS-F-14` — the estate's vector half is ready and the SDK's is not

**Carried at `D-GATE-cp-16` as coverage evidence only: ABS passages have
embeddings, CP-16 does not implement vector Similarity, and no embedding SDK
work is authorized from this rung.**
**Category 3, and it INVERTS the evidence recorded at rung 19.** All **1,882**
ABS passages carry a 1536-dimension `text-embedding-3-small` embedding. At
cp-19 the vector path was blocked by the *estate* (72 advisory passages, no
embeddings); here the estate is ready and the blocker is entirely the SDK side —
no embedder ships and the builder wires no vector substrate. The lexical
operator is used, as at cp-19.

| §I field | |
|---|---|
| **capability** | a shipped embedder adapter and a vector substrate the builder can wire from configuration |
| **evidence / rungs** | cp-13-canonical, cp-19 (`CP17-F-12` family), **cp-16 (`ABS-F-14`) — first rung where the data is ready** |
| **current supported path** | `TokenOverlapIndex`, the SDK's lexical operator, over a composed corpus |
| **friction** | the ranked corpus is lexical where the estate could support semantic ranking; no adopter-visible way to use embeddings that already exist |
| **adoption impact** | any adopter whose document store already carries embeddings |
| **launch necessity** | §C step 1 **yes, we can ship without it** (the lexical path satisfies the contract); §C step 2 **no** — the supported path works and is not error-prone |
| **scope / risk** | an `EmbedderProtocol` adapter plus a similarity-source binding; touches `D-IMPL-03`/`D-IMPL-07` |
| **recommended release** | post-launch |

---

## 5 · Estate / example limitations (§K.5)

### `ABS-F-01` — a representative sample costs what a full scan costs

**Recorded at `D-GATE-cp-16`: sampling can reduce materialized rows without
reducing the underlying blocks read. The warm measurements stand and the
cold-cache interpretation is rejected. No claim is made that `LIMIT` is
generally a cost optimization.**
**The rung's most useful measurement, and it is counter-intuitive.** Measured
on `SDART-2022-6` / `2026-06`, five warm runs each, block counts stable to a
single distinct value:

| approach | rows materialized | blocks scanned | representative? |
|---|---:|---:|---|
| full partition | 35,814 | 1,849 | yes — but it materializes the pool |
| prefix `LIMIT 200` | 200 | **16** | **no** — and ABS-EE ordering makes a prefix misleading |
| stratified by deterministic hash | 166 | **1,849** | **yes** |
| cohort aggregate | 4 | 2 | n/a |
| deal state | 1 | 7 | n/a |

**Sampling saves MATERIALIZATION, not blocks.** A representative sample must
touch the partition; only a prefix avoids that, and the prefix is the thing the
source specification forbids. This is exactly why the ruling asks for *records
and blocks* — rows alone would call the prefix a 178× win. A first, un-warmed
measurement of the prefix read **116,134** blocks and I nearly recorded it as
*"`LIMIT` is 63× worse than a full scan"*; the warm re-measurement refuted it.
A single un-warmed number is not a cost statement.

### `ABS-F-02` — the stratification key is itself a restricted field
The source specification asks for a sample *stratified across cohorts*. The
cohort key is `credit_band`, which derives from `obligor_credit_score` — one of
the four fields the estate's own `ex:LoanLevelPrivacyConstraint` nodes restrict
to `cohort` granularity. A band-stratified loan sample would therefore disclose
a score bucket per loan. **Binding:** the sample is uniform over the partition
by a deterministic hash — representative in expectation, stable across runs, and
carrying none of the four restricted fields. Recorded rather than silently
substituted, because it is a departure from the source specification.

### `ABS-F-03` — the filed report and the in-force definition disagree
`abs_servicer_report.published_delinquency_trigger` reads **24.00 %** in every
one of the twelve periods, including those after the amendment's `valid_from`.
So at `as_of ≥ 2025-11-01` the filed 10-D publishes the original threshold while
the ledger's in-force definition is the amended **13.50 %**. This is honest: the
amendment is engineered and was never filed, so no filed document could carry
it. **Binding:** the product serves **both** — the in-force definition under
`triggers`, and the filed figure under `pool_performance.published_delinquency_trigger`
— and prefers neither silently. The consequence is the rung's whole point: read
the filed report and you believe you have ~12.8 points of headroom; read the
in-force definition and it is **2.32**.

### `ABS-F-05` — the ceiling table joins to no principal register
`abs_granularity_entitlement.principal` holds role names
(`structured-finance-desk`, `credit-risk`, `client-reporting`) that match
**nothing** in `ccf_v2.principal`, whose four rows carry unrelated perspectives.
**No join is invented**: the deployment declares the credential → principal →
role chain itself, as rungs 17, 18 and 19 did, and the estate's rows are read as
the **evidence** the Control Plane constraint must agree with (`ABS-G11`). Rung
15's estate-supplied mapping was the exception, not the rule.

### `ABS-F-10` — an evidence-anchored TTL cannot serve an empty subject

**Posture kept at `D-GATE-cp-16`: a different mechanism from the computed-empty
cases of earlier rungs, serving the same no-oracle governance objective.**
A question with no evidence at the instant has nothing to anchor its expiry on,
so it is **refused** (`ttl-anchor-unresolvable`) rather than served
computed-empty as rung 15's product was. **Measured, because the governance
question is whether this leaks existence:** a deal that does not exist, a real
deal with no reporting period, and a nonexistent deal at an out-of-window
instant are refused **identically**. There is no existence oracle — the
distinction exposed is *is there evidence at this instant*, a property of the
question rather than of the subject. Gated at `ABS-G22`.

### `ABS-F-15` — a historical question must be decided at its own instant
Because `as_of` is both the reporting period and the decision instant, asking
about `2025-09` from today yields evidence nine months old and the 24-hour
evidence-anchored TTL refuses it. The demonstration therefore *decides* at the
instant it asks about, which is the honest forensic framing. Disclosed here and
in the README with the illustrative-calibration wording (`D-IMPL-323`).

---

## 6 · Proof-machinery defects — mine, corrected, recorded

Four, all found by sabotage and none by reading. Consistent with the standing
lesson that **a sabotage which cannot redden its gate is a proof-machinery
defect, not a passing gate**.

### `ABS-F-07` — the estate could not tell a sort from a coincidence
Removing the seniority sort entirely left `ABS-G02` **green**: every tranche
identifier in this estate sorts into seniority order, so the two orderings
coincide. Corrected with an in-process positive control whose identifiers
disagree with its seniority. The estate alone cannot prove this gate.

### `ABS-F-08` — the served payload cannot prove where a bound was applied

**CARRIED at `D-GATE-cp-16`. This is the existing residual `341-1` becoming
observable; no further SDK phase is opened.**
Removing the `filed_date <= as_of` bound from the statement left `ABS-G05`
**green**, because the temporal operator *also* cuts at the boundary and the
served rows were identical. **This is residual `341-1`'s entire point:** whether
acquisition was bounded at the decision instant or everything was acquired and
filtered afterwards is **invisible in the product**. Corrected: the gate now
reads what acquisition *materialized*. Worth carrying forward — any rung
asserting acquisition-side bounding from a payload is asserting nothing.

### `ABS-F-09` — a sabotage that targeted the wrong claim
Pinning the payload's `as_of` to a constant left `ABS-G21` green, because the
two determinations differ in their trigger sets too. Corrected to a sabotage
that actually collapses them: make the period reader ignore the instant.

### `ABS-F-04` — reading an unordered collection as a sequence, caught

**Recorded at `D-GATE-cp-16`: `operators_invoked` is an unordered `frozenset`
and must not be used to prove execution order. The ordered operator plan is held
in replay dimension 5 and is the correct evidence.**
`ContextProductContract.lineage.operators_invoked` is a **`frozenset`**. My
first `ABS-G01` asserted an ordering against it, which is meaningless, and it
failed loudly rather than passing by luck. The executed order lives in replay
dimension 5 as `content_generation_path.operator_plan`, an ordered tuple. The
gate now reads that. **Note for rungs 15 and 19**, whose equivalent gates are
recorded `unavailable`: the ordering *is* assertable from the replay record even
though the sabotage remains unavailable, because `CATEGORY_ORDER` still makes
the forbidden order unreachable from a deployment.

### And one where the SDK refused to guess — correctly
Declaring `trigger` as the similarity corpus class failed with
`SimilarityCorpusAttributeError`: the corpus attribute must exist on **every**
member of a ranked class, and the unanchored threshold has no filed text. The
SDK refused rather than guessing, and the refusal pushed the model to the shape
Route B actually requires — **an anchor is its own class, so an unanchored
threshold has no anchor node at all** rather than an anchor node with empty
fields. Good SDK behavior, recorded because it changed the design.

---

## 7 · Product result (§K.6)

At `SDART-2022-6`, `as_of 2026-06-30`, as the structured-finance desk at
`tranche` granularity: pool balance 320,202,755.30 against 23,525 receivables,
delinquency **11.18 %**; three trigger definitions in force; the delinquency
trigger is the **amended 13.50 %**, served **unanchored** and classified
`engineered`, with proximity **2.32 points** and `breached=false`; the filed
servicer report still publishes 24.00 %. Two findings are named. Assembly:
12 records materialized, 25 blocks, band `aggregate-scale`.

**What a consumer may rely on:** the in-force definition at the instant it
asked; that every publicly sourced threshold resolves to filed text it can
re-hash; that any threshold without filed text is named; that it received no
granularity above its role's ceiling; and what the answer cost.

**What it may not rely on:** per-deal repurchase attribution (there is none);
a numeric distance for a formula-defined threshold; loan-level borrower
attributes at any sample size; or the filed servicer figure agreeing with the
in-force definition after an amendment.

## Security remediation — `EX-01`, `EX-09` (2026-10-07)

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before the change: §B.4, the example's own code rather than the SDK. Changed under `D-IMPL-261`'s "objectively wrong" reason, authorized by `D-IMPL-376` ruling (7): *"SDK input rejection is useful defense, but leaves fragile example code for adopters to copy."* The SDK half — `ProductRequest.subject` had no shape — was closed by `D-IMPL-357`'s subject floor, which refuses these values at the door; the guard here holds in-process, below it.

- **`EX-01`.** The deal IRI — the configured prefix plus the caller's deal id — was spliced into a SPARQL `<…>` position in `acquisition.py::_Graph.triggers`, which `acquisition.py::acquire` reaches for the watermark BEFORE the deal-existence check, so the splice fired whether or not the deal exists. The IRI now passes through `acquisition.py::_iri` — cp-14's approach, held to the whole SPARQL 1.1 `IRIREF` grammar and matched whole, so a trailing newline is refused too — before any store is read.
- **`EX-09`.** `acquisition.py::_Relational.rows` and `::_Relational.rows_and_cost` built `SET search_path TO {schema}` by f-string (security review 2026-09-23). It now composes the statement with the driver's own `psycopg.sql` — `SQL("SET search_path TO {}").format(Identifier(schema))` — so the configured schema reaches PostgreSQL as one quoted identifier, whatever it contains. The documented schema `ccf_v2` is one lowercase identifier, so it names the same schema quoted or not.

No served output moves: for every value the guard admits, the query text is byte-identical to before (measured on the demonstration subjects). Evidence: `tests/examples/test_ex_01_sparql_value_placement.py`, `tests/examples/test_ex_09_search_path_identifier.py`.
