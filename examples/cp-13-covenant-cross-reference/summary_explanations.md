# cp-13 — what each run shows, what you would have missed, and how it works

Three readers are served here: a **technical product manager** deciding whether
this capability is worth having, an **engineer** who has to build or extend it,
and a **credit SME** who knows what a covenant test actually costs to get wrong.
Each run is given as *the output*, *what you would have missed*, and *how the
mechanism produces it*.

---

## Run 1 — the demonstration question

```
make -s example-cp-13
```

Four evidence nodes, `credit-officer`, `filed` scope, as of 2026-09-13.

### The output

```
SEEDED ON    ex:PassageAnchor   (4 sources, depth 3)

ENVELOPE     credit-officer / filed
  permitted classifications  ['public-filed']
  permitted documents        160   (excluded for no classification: 49)
  retrieval bound            before-ranking   filter={'classification': {'$in': ['public-filed']}}
  candidates examined        0
  NOT EVALUABLE              0  (no-embedding)

CITATIONS    4 CHECKED over 21 chain nodes
  not evidenced 17, and every one carries a reason:
      span-unverifiable           4
      point-anchor               13

context debt D_c 0.8095   F 1  C 0.1905  S 1.0000
```

### What you would have missed

**For the SME.** Four covenants, and the product can evidence the *covenant*
text for each — but not one of the **definitions** underneath. Every
`CovenantDefinition` node in view carries a span whose text is exactly right and
which nothing can check. If you are testing compliance against *which EBITDA*,
this product tells you plainly that it cannot show you the sentence. That is the
answer you need, and it is the one a retrieval pipeline would have hidden by
returning the text anyway.

**For the PM.** `C 0.1905` is not a quality problem in the assembly. It is the
measured completeness of the *evidence*: 4 of 21 chain nodes can be cited. The
product's job here is to make that number visible rather than to make it look
better.

**For the engineer.** Every one of the 17 absences carries a reason from a
**closed** vocabulary, and the declared product gate refuses a serve where one
does not. An unexplained omission would make *"we could not evidence this"*
indistinguishable from *"we did not look"*.

### How it works

`acquisition._cite` is the single path from a chain node to quoted text, and it
has no second constructor: follow `ex:evidencedBy` to a passage IRI, resolve
that passage **by id**, read *its own* offsets and sha256, cut the span **by
offset** — never by re-searching for the text, which can match a different
occurrence and silently relocate the citation — re-hash, compare. Anything that
fails returns `Uncitable`.

---

## Run 2 — the widened envelope

```
make -s example-cp-13 PRINCIPAL=control-room CORPUS_SCOPE=filed-and-internal
```

### The output

```
ENVELOPE     control-room / filed-and-internal
  permitted classifications  ['internal-confidential', 'internal-restricted', 'public-filed']
  retrieval bound            before-ranking
  candidates examined        22
  NOT EVALUABLE              18  (no-embedding)
  hit   62%  MEMO-0020  internal-confidential  Annual review — Sabre Corp
  hit   62%  MEMO-0010  internal-confidential  Annual review — XPO, Inc.
  hit   60%  MEMO-0015  internal-confidential  Annual review — Thermon Group
```

### What you would have missed

**Both numbers, and they say different things.** `22` is what similarity
actually scored. `18` is what it *could not reach* — eligible memoranda with no
embedding. A system that reported only the hits would be telling you it searched
40 documents when it searched 22, and the 18 would present as *nothing relevant
found*.

**For the SME.** Eighteen internal credit opinions are invisible to this search
and the product says so. If one of them is the memo that matters, you now know
to go looking by hand instead of concluding it does not exist.

**For the PM.** `candidates_examined` is the number that makes the policy
envelope auditable from outside. It is in the payload for exactly that reason.

**For the engineer.** The classification bound is an **argument to the MongoDB
query**, not a predicate over its results. That distinction is invisible in the
hits — a post-filter produces the same five — and it is the whole of
Policy-before-Similarity. `CXR-G22` asserts the two mechanisms produce
*identical* hits, because that is what makes counting the scored population the
only available detector.

---

## Run 3 — the refusal

```
make -s example-cp-13 PRINCIPAL=relationship-manager CORPUS_SCOPE=filed-and-internal
```

### The output

```
REFUSED      not-entitled
  principal 'relationship-manager' has no entitlement row for corpus scope
  'filed-and-internal'; refused rather than narrowed
```

### What you would have missed

A narrowed answer. `relationship-manager` may read `filed`, and a helpful system
would quietly serve that instead — answering a question they did not ask, and
hiding that an internal corpus exists at all.

**For the PM.** This is the difference between an entitlement and a filter. The
same principal at `filed` serves normally; the refusal is about the *scope*.

---

## Run 4 — the as-of axis

```
make -s example-cp-13 AS_OF=2025-08-12T00:00:00+00:00
```

### What you would have missed

Which text governs. An amendment is filed *after* it begins governing —
`529900E95812SYWMCE44`'s amendment governs from 2026-06-29 while its base
governs from 2026-06-09 — so a product keyed on the filing date serves the old
text for the gap between them.

**And only four borrowers can demonstrate it.** Seven hold both a base and an
amendment; on three of them both begin governing on the *identical date*, and a
test asserted there would prove nothing because both readings coincide. The gate
selects from the four and asserts the population is four.

---

## The three things this rung exists to teach

1. **Extractable is not auditable, and the dangerous case is the one where the
   text is right.** All 49 definition spans land on exactly the right words and
   none can be checked: no recorded hash, no named passage, no passage even
   covering the span. Measured through the defective mechanism: **48 emitted, 47
   reading as genuine definitions, 0 auditable.** A wrong citation is caught by
   a hash. An unauditable one is caught only by a product that refuses to emit
   what it cannot check — while the text on screen is visibly correct.

2. **A predicate that names a limitation has not lifted it.** `ex:declaredAt`
   arrived mid-build, from the estate owner, and marks 158 nodes as
   *intentionally* a point anchor. It is a real improvement: the product can now
   read *"this is a point"* off the graph instead of inferring it from a missing
   end. It supplies no end offset, so the citation is still not emittable and
   the claim is still Context Debt. Reading the marker as the repair is the
   mistake.

3. **Seed where the evidence is, not where the name matches.** `ex:Covenant` is
   the type whose name answers the question and it reaches depth 3 on **one**
   source. `ex:PassageAnchor` — the evidence node — reaches it on **26**. The
   ontology's vocabulary and the estate's topology are different things, and the
   product declares which one it walked.

---

## A note on how this example changed under its own feet

Mid-build, the estate owner repaired a defect this rung had been specified
around: an anchor-identity collision that merged two covenants onto one URI.
Every measurement in the original finding was correct and **the causal story was
wrong** — this specification said RDF could not pair the literals; the truth was
that the URI omitted the document. The repair recovered a covenant the collision
had been silently overwriting.

The defect is preserved at `CP13-F-01` as `FIXED-upstream` with its original
measurements and its correction intact, and it is **not** recreated as an
executable trap: the source ledger's `t` is ignored on this instance, so the old
state cannot be replayed and this product does not pretend otherwise.
