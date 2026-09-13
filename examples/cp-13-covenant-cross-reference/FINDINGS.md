# cp-13 — findings

**The authoritative findings record for `examples/cp-13-covenant-cross-reference`.**
Every `CP13-F-NN` referenced anywhere in this tree resolves here.

## Status vocabulary

`D-IMPL-261`'s four — **OPEN** / **FIXED-`<phase>`** / **ESTATE-LIMITATION** /
**NOT-A-GAP** — plus one added at this rung on Dave's ruling of 2026-09-13:

> **`FIXED-upstream`** — the **estate or source owner repaired the underlying
> data** after the finding was raised. Materially different from
> `FIXED-gate-1/2`, which is a repair this repository made, and from
> `NOT-A-GAP`, which says there was nothing to repair.
>
> **A `FIXED-upstream` finding keeps its original measurement and its causal
> correction.** The defect was real, the product was specified against it, and
> the history is what explains why the specification reads as it does. Nothing
> here rewrites the past as though those defects never existed.

**Sixteen findings. None OPEN.** No SDK gap was found and none was authorized:
the operator-order and `PassageAnchor` surfaces were sufficient.

---

## Summary

| id | status | one line |
|---|---|---|
| `CP13-F-01` | FIXED-upstream | the anchor-identity collision — 79/43/36, repaired at source, **not replayable** |
| `CP13-F-02` | ESTATE-LIMITATION | `ex:endOffset` absent on all 158 `DefinedTerm` |
| `CP13-F-03` | FIXED-upstream | `ex:declaredAt` was 0, is now 170 — it marks, it does not repair |
| `CP13-F-04` | ESTATE-LIMITATION | the chain does not hang off `ex:Covenant` |
| `CP13-F-05` | FIXED-upstream | "43 nodes" was an assertion count; the real figure was always 44 |
| `CP13-F-06` | ESTATE-LIMITATION | `ex:governedBy` is 0 assertions |
| `CP13-F-07` | ESTATE-LIMITATION | 548 of 37,865 passages carry no `sha256` |
| `CP13-F-08` | ESTATE-LIMITATION | 18 of 40 memoranda carry no embedding |
| `CP13-F-09` | ESTATE-LIMITATION | only 4 of 7 borrowers have a separating `governs_from` |
| `CP13-F-10` | ESTATE-LIMITATION | 49 of 249 documents carry no classification |
| `CP13-F-11` | NOT-A-GAP | one `COVDEF-*` node is typed `ex:Covenant` |
| `CP13-F-12` | FIXED-gate-2 | no λ_c class decays, and `CP13-F-15` is why |
| `CP13-F-13` | FIXED-gate-2 | a Gate-1 figure was taken from a printed sample, not a population |
| `CP13-F-14` | ESTATE-LIMITATION | **the correct span that cannot be audited** — the rung's central trap |
| `CP13-F-15` | FIXED-gate-2 | **the chain has no temporal basis at all**, so `supersede-only` is the only honest behavior |
| `CP13-F-16` | FIXED-gate-2 | a gate asserted execution order off a `frozenset` and passed by luck |

---

## `CP13-F-01` — the anchor-identity collision

**FIXED-upstream.** Raised 2026-09-13, repaired by `ccf-dataprep` the same day.

**As measured (original, and retained):**

```
37 URIs for 44 covenants        6 of them carrying two complete anchors
four-literal join  ->  79 rows      43 valid      36 FALSE
12 of the 36 slice to the empty string (start > end, e.g. 474431 > 400894)
```

**Causal correction.** This specification first attributed it to *RDF being
unable to pair the literals*. **That was wrong.** The node URI was
`COVSRC-{accession}-{covenant_type[:8]}` and **omitted the document**, so six
URIs each absorbed two covenants from two different credit agreements filed in
the same submission — XPO's `ex10-1` and `ex10-2` both carry a leverage
covenant, at different thresholds and different spans.

The numbers were right and the explanation was not. The reification this
specification would have proposed **would have produced a node correctly
carrying two anchors and still no way to know it was two covenants** — it would
have made the data look repaired.

**The repair, applied at source:** re-keyed on `(accession, document,
covenant_type)`.

| | before | after |
|---|---:|---:|
| anchor URIs | 37 for 44 covenants | **44 for 44** |
| four-literal join | 79 rows | **44** |
| anchors hashing correctly | 43 of 79 | **44 of 44** |
| inverted spans | ≥ 1 | **0** |
| untyped nodes | 37 | **0** — now `ex:PassageAnchor` |

**The collision had been silently overwriting one covenant**, so the repair
recovered a record: 44, not 43.

**NOT REPLAYABLE, and this product does not claim otherwise.** The source
ledger's `t` parameter is accepted and **ignored** on this instance — it returns
current state at every value tried, including values well before the
remediation — and `FlureeGraphReader.query_pinned` pins CCF's own L3 rather than
a source ledger. The old state is history. No gate recreates it.

## `CP13-F-02` — every `DefinedTerm` is a point anchor

**ESTATE-LIMITATION.** `ex:endOffset` is absent on **all 158** `DefinedTerm`
nodes; 170 subjects overall carry a start with no end, and **0 carry an end with
no start**, which rules out truncation.

`ex:startOffset` does two jobs under one name: a true span start on
`CovenantDefinition`, and a **point anchor** everywhere else. A point anchor
cannot check a citation — you cannot extract the quoted text from it. Every
depth-3 chain therefore terminates in a node that is located and not quotable,
and the product reports Context Debt rather than a citation (`CXR-G08`,
`CXR-G20`). **No `endOffset` is guessed.**

## `CP13-F-03` — `ex:declaredAt` was absent and is now present

**FIXED-upstream.**

**As measured (original):** 0 assertions. The repair had been accepted upstream
on 2026-09-12 and was not implemented, so the product was specified against the
estate as it was.

**Repaired by the estate owner 2026-09-13:** **170 assertions over 170 subjects,
158 of them on `DefinedTerm`**, appended alongside `startOffset` rather than
narrowing it.

**It distinguishes a point anchor; it does not repair one.** `endOffset` is
still absent on all 158, so `CP13-F-02` stands unchanged and the terminal hop is
still Context Debt. `CXR-G16` asserts both halves: the product reads the
predicate and reports the node as *intentionally a point*, **and** that node
still carries no end offset and emits no citation.

## `CP13-F-04` — the definition chain does not hang off `ex:Covenant`

**ESTATE-LIMITATION.**

```
seed on ex:Covenant (182 nodes):       depth 3 -> 1
seed on ex:PassageAnchor (44 nodes):   depth 3 -> 26
```

The type whose **name** matches the question reaches almost nothing; the type
that carries the **evidence** reaches everything. The product seeds on
`ex:PassageAnchor` and **declares** that it does (`CXR-G12`, `CXR-G21`).

## `CP13-F-05` — "43 nodes" was an assertion count

**FIXED-upstream.**

**As measured (original):** the upstream report of *"43 `COVSRC-*` nodes"* was
43 **assertions** over **37 subjects** — 31 carrying one anchor and 6 carrying
two. Corrected to the peer through the vault, accepted, and it led them to the
real cause: the URI collision of `CP13-F-01`.

**The correct figure was never 43 *or* 37.** It was 44 covenants all along, with
7 of them colliding onto 6 URIs.

## `CP13-F-06` — `ex:governedBy` does not exist

**ESTATE-LIMITATION.** 0 assertions, though the vault's schema for this product
names it as a relationship. **No proxy is substituted.** The payload asserts no
governing edge and declares the leg absent (`CXR-G17`), and the gate re-measures
the predicate so it fires if the estate ever gains one.

## `CP13-F-07` — 548 passages carry no `sha256`

**ESTATE-LIMITATION.** 548 of 37,865, and those same 548 carry no `alignment`,
`heading` or `structure_aligned`. They cannot satisfy passage resolvability and
are **not citable**; the product classifies them `passage-has-no-sha256` rather
than citing them unchecked.

## `CP13-F-08` — 18 of 40 memoranda carry no embedding

**ESTATE-LIMITATION.** They cannot be reached by similarity **at all**.

**An absent embedding is not a search result.** The payload reports them as
`not_evaluable` with reason `no-embedding`, states the count of ranked
candidates beside the count of eligible documents, and lists the ids — so a
consumer can tell *we searched and found nothing* from *we could not search
these at all* (`CXR-G18`). Collapsing the two is the failure mode this product
exists to refuse.

## `CP13-F-09` — only 4 of 7 borrowers have a separating `governs_from`

**ESTATE-LIMITATION.** Seven borrowers hold both a base and an amendment. On
three of them **both begin governing on the identical date**, so an `as_of`
reading cannot distinguish them and a gate asserted there would prove nothing.

`CXR-G13` selects from the four, and **asserts the population is exactly four**,
so a later estate change that collapsed the dates is caught rather than silently
making the gate vacuous.

## `CP13-F-10` — 49 of 249 documents carry no classification

**ESTATE-LIMITATION.** The entitlement rules key on classification, so an
unclassified document has no admitting row. **The product treats absence as NOT
ADMITTED rather than as unrestricted**, and the payload states the excluded
count.

## `CP13-F-11` — one `COVDEF-*` node is typed `ex:Covenant`

**NOT-A-GAP.** 181 `COV-*` plus 1 `COVDEF-*` make the 182. Recorded so a count
keyed on the type is read as what it is.

## `CP13-F-12` — no λ_c class on this product decays

**FIXED-gate-2.** The article's §E declares ~365 days for definition-chain
edges. This estate cannot support it — see `CP13-F-15` — so **there is no
calibration value to disclose**. All three classes are `supersede-only` and `F`
reads **1**, which makes this product's Context Debt a pure **completeness**
story.

That is coherent rather than convenient: filed text is immutable, and what this
product cannot do is *evidence* the chain, not *keep it current*.

## `CP13-F-13` — a Gate-1 figure came from a printed sample

**FIXED-gate-2.** §0.1 said *one* of the 36 false citations hashed to the empty
string; the full run gave **12**. The Gate-1 claim came from a three-row printed
sample rather than from the whole population.

Recorded because the lesson outlives the defect: **a figure taken from a printed
sample is not a measurement of a population**, and the gate caught it only
because it *computed* both mechanisms instead of quoting either. The state it
measured is now `FIXED-upstream` at `CP13-F-01`.

## `CP13-F-14` — the correct span that cannot be audited

**ESTATE-LIMITATION.** This is the rung's central trap and the subject of
`CXR-G19`.

All **49** `CovenantDefinition` nodes carry a real span and nothing to check it
against:

```
48 of 49  startOffset, endOffset, documentId
 0 of 49  passageSha256
 0 of 49  evidencedBy
 0        passages matching or containing the span
```

The extracted text is **exactly right**:

```
"Consolidated Fixed Charge Coverage Ratio" means, for any Measurement Period …
"Consolidated Leverage Ratio": as at the last day of any period, the ratio o…
```

Measured through the gate's own defective mechanism: **48 spans extractable,
47 of them reading as genuine definitions, 0 of them auditable.**

**That is what makes it the hard case.** A wrong citation is caught by a hash.
An unauditable one is caught only by a product that refuses to emit what it
cannot check — and refuses while the text on screen is visibly correct. Emitting
it would be an **asserted** citation, and an asserted citation is
indistinguishable from a checked one in the payload.

Classified `span-unverifiable`, reported as Context Debt with its reason, and
kept distinct from `point-anchor` so the payload says which failure it hit.

**Unlike `CP13-F-01`, this cannot be re-keyed away.** There is no recorded hash
to key to.

## `CP13-F-15` — the chain has no temporal basis, so `supersede-only` is the honest behavior

**FIXED-gate-2. This is not a calibration choice, and it must not be read as
one.**

**There is no instant to decay against.** Measured 2026-09-13, the full
predicate set of each class in the chain is:

```
ex:CovenantDefinition   covenantType · crossReferences · declarationConvention
                        documentId · endOffset · label · provenance
                        startOffset · type · unresolvedTerm
ex:PassageAnchor        anchorVerified · covenantType · definedBy · documentId
                        endOffset · evidencedBy · measuredBy · passageSha256
                        provenance · startOffset · threshold · type
ex:DefinedTerm          declaredAt · documentId · label · provenance
                        startOffset · type
```

**Not one temporal predicate among them** — no extraction instant, no assertion
date, no effective date, nothing. A decaying λ_c has nothing to read.

**The SDK refused rather than letting it be faked.** Declaring `decay_basis:
valid-from` on `cxr_node` made `D-IMPL-331` refuse the serve outright with
`MissingDecayInstant`:

> observation type `cxr_node` declares `decay_basis: valid-from` and this
> observation carries no `valid_from`. Refused rather than read from
> `observed_at`: that instant is when the FABRIC learned the claim, so falling
> back would report a perfectly fresh figure for an observation whose real age
> is unknown — which is the defect the basis exists to end

Falling back would have produced a **freshness figure this deployment could not
justify**, computed from the instant the fabric happened to ingest.

**`supersede-only` is therefore the only honest declaration**, not a tuned one.
It returns retained relevance 1, which is the correct statement for a class with
no clock, and re-extraction on amendment **is** supersession rather than decay.

**This is deliberately NOT an illustrative calibration.** There is no threshold
here that was chosen to make a mechanism observable, no production value being
stood in for, and nothing to disclose under CLAUDE.md §9. The estate carries no
basis; the product declares that, and the SDK is what stopped it from declaring
otherwise.

## `CP13-F-16` — a gate asserted execution order off a `frozenset`

**FIXED-gate-2.**

`CXR-G09`'s first limb — *policy precedes similarity in the resolved plan
order* — read `ProductLineage.operators_invoked`. The contract documents that
field as **"the operator SET the producer declares it ran"** and types it
`frozenset[str]`.

**A set carries no order.** Iterating it yields hash order, which for strings
varies per interpreter. Run alone the gate was green; run beside
`test_cp_12_output.py` in the same process it read:

```
['traversal.typed-neighborhood', 'policy.principal-subgraph']
```

and failed. It had been passing by luck, and the luck held for every run until
another module shared the interpreter.

**The ordered plan is `DecisionReplayRecord.content_generation_path.operator_plan`**,
built from the execution's own steps. The gate now asserts that, asserts the
steps agree with it, and asserts the plan's membership matches the declared set
— so neither field can drift into being a label for the other.

**This is `CP12-F-12`'s defect class in a second rung.** There, `next(iter(a_set))`
chose a comparison peer and moved the content address between processes. Here, a
set was read as a sequence. Both are the same mistake: **an unordered collection
used where order was the claim.**

**And limb (a) turns out to be `unavailable` anyway.** Declaring
`traversal.typed-neighborhood` before `policy.principal-subgraph` in
`required_operator_keys` still produces a policy-first plan — the planner orders
by category — so the bad state is unreachable from this deployment. The gate
stays `passed` on limb (b), where the retrieval bound is genuinely sabotageable.
