# cp-13 — covenant cross-reference

**Rung 13 of the Context Product ladder · `credit-risk.covenant-cross-reference.v1`**
**The first Tier-4 product: MongoDB enters and the evidence becomes text.**

> **What does this covenant actually require?**
>
> Not the threshold — the **definition**. And every claim has to point at the
> text that says so.

## What this demonstrates

A credit officer testing compliance needs which EBITDA, with which addbacks,
over which measurement period, per which section of which agreement. The
threshold is the easy half.

This is the first rung where a claim can be wrong **in a way that looks
completely right**, and the product is built around four refusals:

- **A correct span is not an auditable one.** All 49 `CovenantDefinition` nodes
  carry a span whose offsets land on exactly the right words —
  `"Consolidated Fixed Charge Coverage Ratio" means, for any Measurement
  Period…` — and **none carries a recorded hash or a named passage**, and no
  indexed passage covers it. Measured: **48 extractable, 47 reading as genuine
  definitions, 0 auditable.** Emitting them would feel safe and would be an
  *asserted* citation rather than a *checked* one.
- **A predicate that names a limitation has not lifted it.** `ex:declaredAt`
  marks 158 `DefinedTerm` nodes as *intentionally a point anchor*. It supplies
  no end offset. The claim is still Context Debt, and **no `endOffset` is
  guessed**.
- **The policy envelope is an argument to the query, not a filter over its
  results.** A post-filter produces byte-identical hits and has already computed
  similarity against documents the principal may not see. In an MNPI setting
  that computation *is* the leak.
- **A missing embedding is not an empty result.** 18 of 40 memoranda cannot be
  ranked at all. The payload says so, with the count of ranked candidates beside
  the count of eligible documents.

**And the traversal seeds where the evidence is, not where the name matches.**
Seeding on `ex:Covenant` — the typed, plausible choice — reaches depth 3 on
**one** source. Seeding on `ex:PassageAnchor` reaches it on **26**.

## Run it

```bash
export CCF_CP_13_POSTGRES_DSN='postgresql://USER:PASSWORD@HOST:5432/DATABASE'
export CCF_CP_13_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_13_FLUREE_URL=http://HOST:8090
export CCF_CP_13_FLUREE_LEDGER=fibo-v2
export CCF_CP_13_MONGO_URI=mongodb://HOST:27017
export CCF_CP_13_MONGO_DB=fibo_v2

make -s example-cp-13
```

All three stores are read-only here. The namespaces are the **v2** ones and are
**not** in `ccf_dataprep`'s `.env`, which names v1.

The principal is the axis this rung is about:

```bash
make -s example-cp-13 PRINCIPAL=control-room CORPUS_SCOPE=filed-and-internal
make -s example-cp-13 PRINCIPAL=relationship-manager CORPUS_SCOPE=filed-and-internal  # refused
make -s example-cp-13 AS_OF=2025-08-12T00:00:00+00:00
make -s example-cp-13 DEBT_TOLERANCE=0.10
```

## The story

`credit-officer` at `filed` scope gets 160 permitted documents and **4 checked
citations over 21 chain nodes**. The other 17 nodes carry no citation, and every
one of them says why:

```
span-unverifiable    4     correct span, no hash, no named passage
point-anchor        13     declared a point by ex:declaredAt; no end offset
```

`control-room` at `filed-and-internal` reaches all three classifications. The
retrieval examines **22** candidates — the permitted, embedded population — and
reports **18** more as `not-evaluable` for want of an embedding. A post-filter
would have scored the whole corpus and produced the *same five hits*.

`relationship-manager` asking for `filed-and-internal` is **refused**. There is
no entitlement row. Narrowing to `filed` would answer a question they did not
ask and hide that the document class exists.

Context Debt comes back `0.8095` with **F 1, C 0.1905, S 1.0000**. `F` is 1
because nothing in this chain decays — and `C` is low **because most chain nodes
cannot be evidenced**. That is the finding, not a fault in the assembly.

## Artifact-by-artifact

| file | what it carries | why it is not code |
|---|---|---|
| `ccf_config.yaml` | the whole Control Plane: product class, both operators, the request contract, the resolution rules, the λ_c table | delete it and the spine has nothing to interpret (CLAUDE.md §6.4) |
| `artifacts/source-vocabulary.yaml` | every IRI, collection and table this product reads — and `absent_predicates` | naming `ex:governedBy` **absent** is the difference between *we looked and found nothing* and *there is nothing to look at* |
| `artifacts/question.yaml` | the demonstration question, including the `as_of` pin and the principal | the instant a question is asked as-of is the caller's to state |
| `artifacts/gates.yaml` | all 22 declared gates, each with its executing test and the sabotage that proved it | a gate nobody can make fire is a declaration, not a control |
| `backends.yaml` | environment-variable **names** only | no host, no port, no credential, anywhere in this tree |
| `acquisition.py` | the three source legs, and **one rule about citations** | `[ADAPT]` — a citation is a named passage reached through `ex:evidencedBy`, re-hashed before it is emitted |
| `projection.py` | the chain, its checked citations, and the reason for every absence | `[ADAPT]` — it refuses five things, each because one was measured |
| `deployment.py` | vocabulary, envelopes, admission, and the deployment half of one declared gate | `[ADAPT]` |
| `produce.py` | boot, acquire, govern | `[MECHANISM]` — the SDK's calls and none of this deployment's vocabulary |

## Whitepaper / CLAUDE.md sections exercised

- **Whitepaper §7.10.3 / `INV-CH7-19`** — passage-level lineage.
  `ccf.contracts.claims.PassageAnchor` carries every citation; the SDK fixes the
  anchoring *obligation* and the deployment names the vocabulary.
- **Whitepaper §7.3** — the single-writer invariant: `booted.handle.worker` is
  the only write handle in the process.
- **Whitepaper §7.4 / §7.5** — two operators and one projection composed by the
  SDK. The deployment authors **no operator set**.
- **Whitepaper §6.3 / §7.6** — the four request axes as fields, the typed
  contract, the three validation gates.
- **Whitepaper §7.7** — `λ_c` and `D_c`, here as a pure completeness story
  because nothing in the chain decays (`CP13-F-15`).
- **Whitepaper §8.7.2 / §7.4** — Policy-before-Similarity, on both limbs.
- **CLAUDE.md §6.4** — the No-Hardcoding Rule.
- **CLAUDE.md §9** — the curated estate as evidence; examples as probes.

## What to change first

**Change the principal.** `PRINCIPAL=control-room CORPUS_SCOPE=filed-and-internal`
and watch the permitted set, the candidates examined and the content address all
move together. That one flag is the difference between a policy envelope and a
filter.

After that, in order of how much they teach:

1. **`PRINCIPAL=relationship-manager CORPUS_SCOPE=filed-and-internal`** — a
   refusal rather than a narrower answer.
2. **`AS_OF`** before an amendment's `governs_from`, on one of the four
   borrowers whose dates separate — fewer documents govern.
3. **The `absent_predicates` block** in `artifacts/source-vocabulary.yaml` —
   delete `governedBy` and the product stops declaring the leg absent.
4. **The λ_c row for `cxr_node`** — set `decay_basis: valid-from` and the SDK
   refuses the serve, because the chain carries no instant at all
   (`CP13-F-15`).

## What would fail

- **Joining `startOffset`, `endOffset`, `passageSha256` and `evidencedBy`
  independently.** Prohibited. The citation unit is the named passage
  (`CXR-G07`).
- **Emitting a definition span because the text is right.** 48 citations, 0 of
  them auditable (`CXR-G19`).
- **Reading `ex:declaredAt` as a repair.** It marks the point anchor; it
  supplies no span (`CXR-G16`).
- **Guessing an `endOffset`** for any of the 158 `DefinedTerm` nodes
  (`CXR-G20`).
- **Seeding on `ex:Covenant`** — depth 3 on one source instead of 26
  (`CXR-G21`).
- **Retrieving broadly and post-filtering.** The hits are identical; the scored
  population is not (`CXR-G22`).
- **Reading a missing embedding as "nothing relevant found"** (`CXR-G18`).
- **Selecting the governing text by `filed_date`.** An amendment is filed after
  it begins governing (`CXR-G11`).
- **Inventing `ex:governedBy`,** which the published schema names and this
  estate does not have (`CXR-G17`).

All 22 gates are in `artifacts/gates.yaml`, all 22 are executed by
`tests/examples/test_cp_13_output.py`, and **all 22 were observed going red
under a sabotage of the mechanism they name** — 19 by breaking this deployment,
3 because the SDK refuses the bad state before this deployment can reach it.
**Four were green under their first sabotage; all four were test defects, and
each is recorded with what was wrong.**
