# The cp-05 remediation set — every surviving finding, in four buckets

**Requested by Dave, 2026-09-08**, after the branch separation: *"turn the surviving cp-05
findings into a very small remediation set, separating: (1) true SDK semantic/architecture
gaps, (2) API/adoption-surface problems, (3) documentation/discoverability problems, (4)
things that require a Dave ruling before implementation. That should keep us from falling
back into another generalized hardening phase."*

**INVENTORY ONLY. NOTHING HERE IS AUTHORIZED, SCOPED, PLANNED OR PHASED.** No file under
`src/`, `runtime/` or `tests/` has been touched. Every row is a classification of something
already recorded — in `CP-SPEC-005` §F.4, in `D-IMPL-277`, or in `D-IMPL-278`'s disposition
table — and carries the citation that lets a reader check it against the record rather than
against this document.

**Each remediation row is held to `D-IMPL-276`'s three gates** — product relevance, evidence
of need, smallest sufficient response — and states all three. A row that cannot state
evidence from a real Context Product does not belong here.

**The denominator is visible.** `CP-SPEC-005` §F.4 carries **19** findings and `D-IMPL-278`
adds **3** dispositions that are not §F.4 rows. Of those 22, **12** are remediation rows and
**10** are not; the ten are enumerated in §5 so nothing is quietly dropped.

---

## Summary

| Bucket | rows | ids |
| --- | --- | --- |
| **1 · SDK semantic / architecture gap** | 2 | `R-01`, `R-02` |
| **2 · API / adoption-surface problem** | 4 | `R-03`, `R-04`, `R-05`, `R-06` |
| **3 · Documentation / discoverability** | 2 | `R-07`, `R-08` |
| **4 · Needs a Dave ruling before implementation** | 4 | `R-09`, `R-10`, `R-11`, `R-12` |

**Two rows carry the weight.** `R-01` is the reconciliation Dave named as the architectural
statement; `R-03` is the adoption-surface gap he called *"probably the most consequential
finding in the entire example."* The other ten are small, and several are one-line changes or
one paragraph of prose.

---

## 1 · SDK semantic / architecture gaps

### `R-01` — delivery does not reconcile the declared product against the observed execution

**Dave's statement of it:** *"CCF has a governed execution spine, but it does not make that
spine the canonical path, nor does it verify that the product being delivered is the product
that spine actually governed."* And: *"the bytes about to leave are the governed determination
represented by that replay record. That is the reconciliation CCF is currently missing."*

| Gate | |
| --- | --- |
| **Product relevance** | cp-05 shipped a 77-member answer produced by a walk that bypassed its own policy operator. Nothing at any boundary noticed. |
| **Evidence of need** | Measured: a `ServedProduct` whose payload claims **9,999** family members, wrapping a replay record whose dimension 1 observed **77**, crosses `ccf.products.door::served_answer` unremarked. Independently, `CP-SPEC-005` §F.4 finding 14 is the same disagreement arising by accident rather than by construction. |
| **Smallest sufficient response** | Both operands are already in the boundary's hand — the payload on `ServedProduct.product`, the record at `ServedProduct.replay_ref`. What shape the comparison takes, what it compares, and whether it lives at `serve`, at the door, or at both is **not decided here**. |

**Citations:** `CP-SPEC-005` §D.10 question 1, §F.4 findings 14 and 18; `D-IMPL-278` row 1;
`D-IMPL-260` P-A (the shape proof this row finds insufficient).

**Not in scope of this row:** making the spine canonical. That is `R-03`.

### `R-02` — determinism enforcement is not uniform across outcomes

**Dave's observation:** *"the float surfacing only on the served/content-hashed path shows
that determinism enforcement is not uniform across all outcomes."*

| Gate | |
| --- | --- |
| **Product relevance** | cp-05 carried a Python float in `request.materiality` through every **withheld** run without complaint, and was refused the first time a run was **served**. |
| **Evidence of need** | `ccf.contracts.canonical` refuses a float — *"not bit-stable across platforms; use int or decimal.Decimal"* — but only the served path content-hashes the product payload. A withheld determination's record never hashes it. Measured on cp-05: six withheld runs green, the first served run red. |
| **Smallest sufficient response** | Unknown; plausibly the refusal envelope's evidence should canonicalize the payload it describes, or the candidate contract should be canonicalized at construction. **Not decided here.** Dave: *"I would hold both behind the larger question until MCP is complete"* — MCP is now complete, so this is unblocked. |

**Citations:** `CP-SPEC-005` §F.4 finding 15.

---

## 2 · API / adoption-surface problems

### `R-03` — the governed spine exists and is not the canonical author path

**Dave's disposition, verbatim:** *"You effectively rediscovered the intended CCF programming
model by hand. That tells us the architecture is substantially there, but the product surface
is wrong. … That is beyond documentation friction. I would classify it as an
adoption-surface/design gap: the safest governed path is not the path of least resistance."*

| Gate | |
| --- | --- |
| **Product relevance** | cp-05 hand-built `refuse_intent → resolve_effective_request → GraphView → operator registry → ProjectionEngine → register_product_class → candidate contract → run_gates → refuse_over_tolerance → build_replay_record → serve` across two work steps, and found `ccf.products.resolver::GovernedResolver` — which composes exactly that — only while wiring the MCP door. |
| **Evidence of need** | Four instances of one pattern in one product: `CP-SPEC-005` §F.4 findings 8 (acquisition), 12 (fulfillment), 14 (policy composition) and 17 (the whole spine). In every case the SDK mechanism was present and correct and the author built beside it. |
| **Smallest sufficient response** | **Not decided here.** What cp-05 measured is what adoption would need: a `plan_factory` seam that can carry a second store's enrichment, an `AssemblyDebtScorerProtocol` override for evidence the `GraphView` does not hold, a home for a product-specific gate (`R-11`), and an answer to acquisition (`R-09`). Each is tractable; none is documented as the path. |

**Citations:** `CP-SPEC-005` §D.10, §F.4 findings 8, 12, 14, 17; `D-IMPL-278` row 2.

### `R-04` — MCP exposure is roughly half application, not binding

**Dave's disposition, verbatim:** *"204 executable lines is still another application, not
configuration and binding. … The 72 lines of resolver/refusal application logic and the
requirement to understand three MCP auth internals are the clearest evidence. The 60 lines of
genuine binding are much closer to what should remain."*

| Gate | |
| --- | --- |
| **Product relevance** | cp-05 came to the door with its governed path already built and still spent 204 executable lines. |
| **Evidence of need** | Measured, blank lines / comments / docstrings excluded: cp-04's door **260**, cp-05's **204** — a 22% reduction. Of cp-05's 204: **60** binding (`build_egress_server` + collaborators), **41** resolver adapter, **31** refusals minted by hand because the SDK ships no constructor for "this door was addressed for the wrong class" or "this parameterized class has no standing answer", **30** imports across 8 SDK modules plus three MCP auth internals (`auth_context_var`, `AuthenticatedUser`, `AccessToken`), **42** plumbing. |
| **Smallest sufficient response** | **Not decided here.** The 60 binding lines are the target shape; the 72 application lines are where the reduction has to come from. |

**Citations:** `CP-SPEC-005` §D.10 question 2; `D-IMPL-278` row 4.

### `R-05` — `refuse_bound_payload` is on no shipped path

**Dave's reclassification, verbatim:** *"a product class that declares a payload schema could
have that schema silently unenforced. Given that no shipped example currently declares such a
schema, I would classify that as a delivery/adoption gap with latent correctness risk, not an
observed correctness defect in the current product path."*

| Gate | |
| --- | --- |
| **Product relevance** | cp-05's door had to state, in prose, that it does not call this function and why — because the resolver Protocol's own docstring requires the call. |
| **Evidence of need** | The only call site in the tree is `archive/examples/04-cross-process/producer_child.py`. No shipped module calls it; `GovernedResolver` does not. It returns `None` for a class declaring no schema, and no shipped example declares one, so it bites nobody **today**. |
| **Smallest sufficient response** | **Not decided here.** Folds naturally into `R-03` or `R-04` rather than standing alone. |

**Citations:** `CP-SPEC-005` §F.4 finding 19 (the surviving half); `D-IMPL-278` row 3 as reclassified;
`D-IMPL-113`, `D-IMPL-121`.

**THE OTHER HALF OF FINDING 19 WAS FALSE AND IS NOT A ROW.** The claim that `GovernedResolver`
leaves the request boundary unchecked was measured false on every limb — address, tier,
undeclared, missing-required, mistyped, declared domain — each with a passing positive control.
Dave: *"there is no SDK correctness defect there and I would not authorize a code change for it."*

### `R-06` — the L1 envelope's identity keys are flat siblings, not nested under the match key

**Dave's classification when it was raised:** *"primarily an adoption ergonomics problem."*

| Gate | |
| --- | --- |
| **Product relevance** | cp-05's first ingest minted nothing: *"matched rule for 'exposure_member' but lacks identity keys ['entity_uri']; the fabric refuses to mint a URI from partial identity."* |
| **Evidence of need** | `AssemblyWorker`'s resolver asks `rule.match_key in payload` and then reads every identity and attribute key from the **top level** of the same mapping. The match key is a presence flag; the declaration alone does not say so. Refusing to mint from partial identity is right; the shape that provokes it is easy to get wrong. |
| **Smallest sufficient response** | Plausibly one sentence in the resolution-spec docstring, or a refusal message that names the expected shape. **Not decided here.** |

**Citations:** `CP-SPEC-005` §F.4 finding 6.

---

## 3 · Documentation / discoverability

### `R-07` — `ProjectionPlan.invoke` receives no request, and an author has to discover where a per-request projection parameter lives

| Gate | |
| --- | --- |
| **Product relevance** | cp-05's materiality threshold is caller-selectable and had to arrive through the plan's constructor. |
| **Evidence of need** | `invoke` takes `view`, `operator_outputs`, `perspective`, `temporal_boundary` and no request. `ProjectionEngine.execute` needed **no adaptation** once the plan was built per request, so this is a discoverability cost rather than a capability gap — and arguably correct as designed. |
| **Smallest sufficient response** | A sentence on `ProjectionPlan` saying the plan, not the call, is where a per-request projection parameter lives. |

**Citations:** `CP-SPEC-005` §F.4 finding 9.

### `R-08` — the `DEBT_TOLERANCE_PARAMETER` narrowing exception is documented where the SDK maintainer reads, not where the author meets it

| Gate | |
| --- | --- |
| **Product relevance** | cp-05 declared two policy constraints with the same `maximum` operator; one refuses and one narrows. It read as an inconsistency until `src/ccf/products/constraints.py` was opened. |
| **Evidence of need** | The behavior is correct and deliberate — *"the one exception to 'nothing is clamped'"* — for the right reason: a fitness bar cannot be refused before fitness has been measured. **This is NOT a gap** (`CP-SPEC-005` §F.4 finding 11 records it as confirmed SDK behavior). But a reader meeting the asymmetry for the first time reaches for the wrong conclusion, as this author did. |
| **Smallest sufficient response** | Name the exception where a deployment declares a policy constraint, not only where the resolver implements one. |

**Citations:** `CP-SPEC-005` §F.4 finding 11, §D.8.

---

## 4 · Needs a Dave ruling before implementation

### `R-09` — no acquisition boundary for an external graph store

**Status: `D-IMPL-277`, OPEN, already awaiting Dave.** Two Context Products have now
hand-rolled SPARQL around its absence. `GovernedResolver` assumes L3 is already populated, so
this row also blocks part of `R-03`. Dave: *"That one deserves a ruling before more hand-coded
SPARQL proliferates."*

### `R-10` — operator seed classes and resolution-produced entity classes can be compositionally incompatible with no boot-time refusal

cp-05 minted its anchor as `exposure_member` while the declared traversal seeds on
`exposure_anchor`; the traversal returned nothing and the estate was fully populated. Dave, when
it was raised: *"I would record that as: Candidate SDK validation gap … I would not fix it
yet."* Recorded as a candidate, not a confirmed gap.

**Citations:** `CP-SPEC-005` §F.4 finding 7.

### `R-11` — a product-specific validation gate has no declared home

cp-05's reconciliation guard — the one gate that catches a *plausible wrong answer* rather than
a broken pipeline — is called from the example's own spine. `run_gates` runs the SDK's set and
has no seam for a product's own. Adopting `GovernedResolver` would strand it. Dave dispositioned
this **candidate SDK extension-point gap**; `D-IMPL-224` already ruled that product gates are
CI-checked declarations, so the ruling needed is whether they also become executable at the
governed path.

**Citations:** `CP-SPEC-005` §D.7; `D-IMPL-278` row 6; `D-IMPL-224`.

### `R-12` — the Control Plane document has no slot for a deployment's own replay binding

Adding a `replay:` section to `ccf_config.yaml` is refused by name, and the refusal is right — a
Control Plane document that accepted arbitrary sections would let a deployment smuggle unaudited
state into the audit plane. But the artifact classes a deployment files its decision records
under have nowhere declared to live: cp-04 put them in `deployment.py` as module constants,
cp-05 in `artifacts/replay.yaml`. Neither is the Control Plane. Dave: *"replay binding having no
natural Control Plane slot suggests deployment governance is still partly outside the
declarative model."*

**Citations:** `CP-SPEC-005` §F.4 finding 16; `examples/cp-05-credit-exposure-rollup/artifacts/replay.yaml`.

---

## 5 · The ten rows that are NOT remediation items

Listed so the denominator is visible and nothing is quietly dropped.

| §F.4 | what it is | why not a remediation row |
| --- | --- | --- |
| 1 | 22 distinct borrowers against the vault's ~50 anchors | **ESTATE** — the estate exceeds the manufacture envelope; a property of the data load |
| 2 | one of 14 reconciliations is `plausible = false` | **ESTATE** — engineered data, and measured NOT in the demonstrated family |
| 3 | the anchor sat below its own materiality floor | **RESOLVED IN cp-05** — L5 now applies the threshold; the assembler returns complete truth |
| 4 | the slug↔LEI join hazard | **ESTATE** — a property of how the ledger names nodes |
| 5 | the vault article's worked anchor does not exist in the estate | **VAULT RETURN PATH** — belongs on the article, not the SDK |
| 8 | guard placement is load-bearing | **RESOLVED IN cp-05** — the empty-operator guard moved to the operator's output; an example lesson |
| 10 | `assembly_mode`, `out_of_scope`, `sdk_spec` null in the vault front matter | **VAULT RETURN PATH** |
| 11 | the `debt_tolerance` narrowing | **NOT A GAP** — confirmed deliberate against the source. Its discoverability half is `R-08` |
| 13 | two self-inflicted documentation defects | **AUTHOR DEFECT** — a fabricated refusal message and an unparseable artifact; corrected in place, correction preserved |
| 14 | the declared policy operator's output was discarded | **FIXED IN cp-05**, sabotage-verified both ways. What it *left* is `R-01` |

Two further items from `D-IMPL-278` are also not rows: the **product-specific debt scorer** is an
expected extension point and worked as designed (`AssemblyDebtScorerProtocol` has a documented
override path), and the **retracted request-boundary claim** is recorded under `R-05` above.

**Roster check.** §F.4 findings 1–19 plus `D-IMPL-278`'s three non-§F.4 dispositions = 22.
Remediation rows `R-01`..`R-12` draw on findings 6, 7, 9, 11, 15, 16, 17, 18, 19 and
`D-IMPL-277`, `D-IMPL-278` rows 4 and 6 — with findings 8, 12 and 14 folded into `R-01`/`R-03`
as evidence rather than as separate rows. The ten above plus the two extension-point items
account for the remainder. Every id in the summary appears in the body and vice versa.

---

## What this document does not do

It does not scope, sequence, phase, estimate or authorize any row. It does not choose between
candidate responses where more than one is plausible. It does not decide whether `R-01` is
enforced at `serve`, at the door, or at both. It does not assign phase numbers. Those are
Dave's, and `D-IMPL-276` is explicit that the response to each must be the smallest sufficient
one, taken against a real Context Product rather than against a class of imagined ones.
