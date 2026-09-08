# Seven proposed SDK changes — current surface, smallest change, ownership, regression evidence

**Requested by Dave, 2026-09-08** (`D-IMPL-279`): *"turn R-01, R-02, R-03, R-09, R-10, R-11,
R-12 into proposed SDK changes with one row each: current surface → smallest change → exact
ownership layer → direct regression evidence. No phase machinery, no new criteria framework,
no generalized proof work. Once that exists, we can decide which changes actually earn code."*

**NOTHING HERE IS AUTHORIZED.** No file under `src/`, `runtime/` or `tests/` has been touched.
Every **current surface** below is a read of the tree at this branch's tip, cited by file and
symbol so it can be checked rather than believed. Every **regression evidence** row names a
single direct test — the `D-IMPL-276` shape, *"one direct regression test"* — and says what it
would assert and what it would go red on.

**Rows carried unruled and NOT in this set:** `R-04` (MCP is half application), `R-05`
(`refuse_bound_payload` on no shipped path), `R-06` (flat envelope shape), `R-07`
(`ProjectionPlan.invoke` takes no request), `R-08` (the debt-tolerance narrowing is
under-documented).

---

## Two measurements that changed what "smallest" means

Both were taken while writing this document, and both make a proposed change smaller than it
looked in `CP-05-REMEDIATION-SET.md`.

**1 · `ccf.replay.serve::serve` ALREADY performs a correspondence check.** It compares
`record.content_generation_path.graph_query_sequence` against the queries it was handed,
element-for-element, and raises `QueryPinMismatch` when they disagree:

> *"the record pins … but the serve seam was handed queries hashing to …; the pinned sequence
> records what ran, so the two must agree element-for-element (D-11, `GQ-20`)"*

So `R-01` is not a new mechanism at a new seam. It is **one more comparison of exactly the
existing shape, at the same seam, over the fact that matters.**

**2 · `ContextProductContract` canonicalizes nothing at construction.** The class has no
validator that touches `canonical_bytes`; the string does not appear in its source at all. The
payload is canonicalized only when something hashes it, and only the served path does. That
locates `R-02` precisely: the shared boundary Dave named is the **vessel's construction**, not
a branch.

---

## The seven rows

### `R-01` — correspondence between the candidate product, the execution and the replay record

| | |
| --- | --- |
| **Current surface** | `ccf.replay.serve::serve(*, product: ServableProduct, record: DecisionReplayRecord, replay_writer, query_pin_writer=None, executed_queries=())`. It already refuses a query-pin disagreement (`QueryPinMismatch`) and then returns `replay_writer.write_replay_record(record=record).deliver(product)`. It does **not** compare the record against the product. `ccf.products.door::served_answer` checks the returned type and never opens the record. |
| **Smallest change** | One comparison in `serve`, before the append: `record.content_generation_path.product_content_address` against `content_hash(product.product)`; refuse on disagreement with a `QueryPinMismatch`-voiced sibling error. Both operands are already in the function. |
| **Ownership layer** | **The governed fulfillment spine** — `src/ccf/replay/serve.py`, which is where `D-IMPL-279` puts it: *"the canonical enforcement point should be in the governed fulfillment spine, before transport encoding."* The door keeps its existing shape check and reconstructs nothing. Nothing changes in `runtime/` or in MCP. |
| **Direct regression evidence** | One test: build a `ServedProduct` whose record describes product **A** and whose vessel is a payload-tampered **B**, and assert `serve` refuses. **Goes red on the shipped tree today** — measured: a vessel claiming 9,999 family members beside a record that observed 77 crosses `served_answer` unremarked. Positive control: the untampered cp-05 pair serves. |
| **Not in this row** | The withheld branch. A refusal carries no vessel, so there is no product address to correspond; `RefusalEvidence` already pins the execution. Widening this row to cover refusals would be inventing a comparison nobody has evidence for. |

### `R-02` — determinism enforcement across every governed outcome

| | |
| --- | --- |
| **Current surface** | `ccf.contracts.canonical::canonical_bytes` refuses a float — *"not bit-stable across platforms; use int or `decimal.Decimal`"* — and is reached only when something hashes. `ContextProductContract` declares **no** validator referencing it (`canonical` appears 0 times in the class source). Measured on cp-05: six **withheld** runs carried a Python float in `request.materiality` green; the first **served** run went red. |
| **Smallest change** | One `model_validator` on `ContextProductContract` that canonicalizes `payload` at construction. The vessel exists on every governed path — served, withheld, and gate-refused — so one check at construction is the shared boundary. |
| **Ownership layer** | **`src/ccf/products/contract.py`** — the vessel, not a branch. `D-IMPL-279`: *"corrected at the canonicalization boundary shared by all governed outcomes, not by sprinkling checks into each branch."* |
| **Direct regression evidence** | One test: construct a `ContextProductContract` with a float in its payload and assert it is refused at construction, with a positive control on the `Decimal` form. **Goes red on the shipped tree today.** |
| **Cost to state honestly** | This makes construction stricter for every existing product. cp-00…cp-05 would each need their payloads checked; cp-05 is already clean. That survey is part of the change, not a surprise after it. |

### `R-03` — make the governed spine the canonical author path

| | |
| --- | --- |
| **Current surface** | `ccf.products.resolver::build_governed_resolver(...)` composes the whole spine and takes 12 required arguments plus 7 optional. It is exercised by tests and by no shipped example. `examples/s1-01-hello-context-product/spine.py` — the SDK's own named worked example for the resolver seam — calls `refuse_request` and does **not** use `GovernedResolver`. cp-05 hand-built the spine across two work steps and found the shipped version only while wiring its MCP door. |
| **Smallest change** | **One worked example that uses it**, plus the `ProductResolverProtocol` and `build_governed_resolver` docstrings pointing at that example as the path. No API change is proposed in this row. |
| **Ownership layer** | **`examples/` and `src/ccf/products/resolver.py` docstrings.** No mechanism moves. |
| **Direct regression evidence** | The worked example runs in CI. That is the evidence: a path nothing exercises is a path nothing keeps working. |
| **Honest limit of this row** | A worked example is the *smallest* response and may not be a *sufficient* one. Four SDK mechanisms were bypassed by a competent author with the docstrings in front of him. Whether the surface itself needs to change — a narrower constructor, a builder that fails loudly when composed by hand — is **not proposed here** and would need its own evidence. This row deliberately proposes the cheap thing first so the expensive thing has to earn itself. |

### `R-09` — a declared acquisition interface

| | |
| --- | --- |
| **Current surface** | Nothing. `src/ccf/graph/backends/` ships six adapters, all of which assume a CCF-owned store; there is no seam for reading someone else's graph and normalizing it toward L2. cp-04 and cp-05 both hand-rolled SPARQL. `GovernedResolver` does `self.fabric.handle.reader.as_of(...)` and assumes L3 is populated. |
| **Smallest change** | A Protocol — an acquisition seam producing normalized envelopes and relationship claims for L2, declared in the Control Plane like any other pluggable substrate — plus the reference implementation CLAUDE.md §11 requires beside every Protocol. **`GovernedResolver` is unchanged**, per the ruling: *"Do not make `GovernedResolver` itself responsible for talking to arbitrary source systems."* |
| **Ownership layer** | **L1/L2 — `src/ccf/signal/` or a new `src/ccf/acquisition/`.** Upstream of the resolver, which keeps source heterogeneity out of the deterministic spine. |
| **Direct regression evidence** | cp-05's own acquisition, rewritten against the Protocol, producing the same 77 nodes and 100 relationship claims. The transcript's byte-reproduction is the assertion. |
| **This is the largest row here** and the only one that adds a new SDK surface. It resolves `D-IMPL-277`, which stood open through two products. |

### `R-10` — reject provably incompatible declarations at boot

| | |
| --- | --- |
| **Current surface** | `src/ccf/deployment/config.py::_refuse_operator_set_divergence` is the **exact precedent**: a boot-time refusal comparing two declarations, refusing rather than picking, *"because only the deployment's author knows which of the two they meant."* No equivalent check exists between a traversal operator's `seed_entity_classes` and the entity classes `resolution.entity_rules` can mint. cp-05 minted its anchor as `exposure_member` against a walk seeding on `exposure_anchor`; the traversal returned nothing over a fully populated estate. |
| **Smallest change** | One more function of the same shape, called from the same site: refuse when a declared `seed_entity_classes` value appears in no `entity_rules[*].entity_class`. **Statically provable from two documents**, which is the whole of what `D-IMPL-279` permits: *"Only validate what can be proven statically; do not infer dynamic cardinality."* |
| **Ownership layer** | **`src/ccf/deployment/config.py`** — Control Plane validation, beside the existing divergence refusal. |
| **Direct regression evidence** | One test: a config whose seed class no entity rule can produce is refused at boot, naming both sides. Positive control: cp-05's current config boots. |

### `R-11` — product gates executable on the governed path

| | |
| --- | --- |
| **Current surface** | `D-IMPL-224` makes product gates **declared and CI-checked**; `tools/check_product_gates.py` and `make product-gates` verify the declarations. Nothing executes one. `run_gates` runs a fixed sequence ending in `GATE_DECLARED_OBLIGATIONS`, whose obligation vocabulary is a **closed `Literal` with one member** and is deliberately SDK-owned: *"a closed `Literal` rather than a free string so that a second obligation is an SDK decision and never a deployment's vocabulary."* cp-05's reconciliation guard — the one gate that catches a plausible wrong answer — is called from the example's own spine and would be stranded by adopting `GovernedResolver`. |
| **Smallest change** | **Not** a new member of that `Literal`, which the existing design explicitly refuses. A separate seam: a deployment-supplied predicate over the candidate product, run by `GovernedResolver` after the candidate exists and before `refuse_over_tolerance`, returning a refusal the existing envelope can carry. |
| **Ownership layer** | **`src/ccf/products/resolver.py`** — the governed spine, at the point `D-IMPL-279` names: *"against the candidate product before serve / refusal determination."* Explicitly **not** `run_gates` (whose vocabulary stays SDK-owned), **not** the MCP door, **not** ad hoc assembler code. |
| **Direct regression evidence** | One test: cp-05's reconciliation guard, declared and executed through the seam, observed **firing** on a hand-built rollup with adjusted > gross and **not firing** on the shipped figures. Both observations already exist as cp-05 evidence; the test moves them onto the governed path. |

### `R-12` — a Control Plane slot for the deployment's replay binding

| | |
| --- | --- |
| **Current surface** | `src/ccf/deployment/config.py::_RESERVED_SECTIONS` is a closed 8-entry mapping; a `replay:` section is refused by name, and the refusal names every recognized alternative. Correct — an open Control Plane document would let a deployment smuggle unaudited state into the audit plane — but the artifact classes a deployment files decision records under have nowhere declared to live. cp-04 put them in `deployment.py` as module constants; cp-05 in `artifacts/replay.yaml`. Neither is the Control Plane. |
| **Smallest change** | One more `_RESERVED_SECTIONS` entry bound to a new `VersionedArtifact` carrying the **binding only** — record class, query-pin class, store selection — and no product-specific replay content, per the ruling: *"only the deployment binding and required policy for replay availability."* |
| **Ownership layer** | **`src/ccf/controlplane/artifacts.py`** (the artifact class) and **`src/ccf/deployment/config.py`** (the section). |
| **Direct regression evidence** | One test: a config declaring `replay:` boots and its binding is readable off the booted fabric; the same config with a product-specific replay field in it is refused. Positive control: a config with no `replay:` section still boots, so the section is optional and no existing deployment breaks. |

---

## What earns code first, if any of it does

Stated as a recommendation, not a decision.

**`R-01` and `R-10` are the two cheapest with the most direct evidence.** Each is one comparison
at a site that already performs a comparison of that exact shape, each has a test that goes red
on the shipped tree today, and neither adds a surface. `R-02` is nearly as cheap but carries a
survey of every existing product's payload.

**`R-09` is the largest and the most consequential**, and it is the one that has already cost two
products a hand-rolled workaround.

**`R-03` is the row this document is least confident about.** Its proposed change — a worked
example — is the smallest thing that could possibly help, and the evidence says four mechanisms
were bypassed by an author who had the docstrings. It is proposed first precisely so that a
larger surface change has to earn itself against a measured failure of the cheap one.
