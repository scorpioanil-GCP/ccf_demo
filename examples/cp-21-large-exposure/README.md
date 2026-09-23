# cp-21 — Large Exposure / Concentration

**The specification is
[`spec/CP-SPEC-021_Large_Exposure_Concentration.md`](spec/CP-SPEC-021_Large_Exposure_Concentration.md)**,
written, reviewed and ruled on before any of this code existed.

## What this demonstrates

Whether one counterparty group's exposure fits inside the limits that actually
bind it — under a regulatory regime selected at the determination instant,
against a capital base whose units are not the units the arithmetic needs, over
a group that **does not exist until this product derives it**.

Four capabilities nothing earlier on the ladder demonstrated:

1. **A DERIVED connected group**, where the caller's `connection_basis` changes
   the membership and therefore the answer (`LEX-G02`, `LEX-G03`, `LEX-G04`).
2. **Normalization at the acquisition boundary with a DECLARED factor**, gated
   on the regulatory consequence rather than on the constant (`LEX-G06`,
   `LEX-G07`).
3. **A limit that is a percentage of capital OR an absolute amount**, selected
   from an effective-dated regime (`LEX-G05`, `LEX-G09`, `LEX-G10`).
4. **A disclosed freshness asymmetry** that is never resolved (`LEX-G14`).

## Run it

```
make -s example-cp-21 CASE="--case breaching"
make -s example-cp-21 CASE="--case fits"
make -s example-cp-21 CASE="--case fits" NO_MITIGATION=--no-mitigation
make -s example-cp-21 CASE="--case basis" CONNECTION_BASIS="--connection-basis control"
```

Needs `CCF_CP_21_POSTGRES_DSN`, `CCF_CP_21_POSTGRES_SCHEMA`,
`CCF_CP_21_FLUREE_URL`, `CCF_CP_21_FLUREE_LEDGER`, `CCF_CP_21_MONGO_URI`,
`CCF_CP_21_MONGO_DB` and the four `CCF_CP_21_TOKEN_*` credentials.
`ccf_environment.yaml` names every one with the remedy for it.

## The story

### The group is derived, and the basis that derives it changes the answer

There is no group registry. The connected group is the transitive closure of
the connection edges the caller's `connection_basis` admits, computed at the
ledger point — `control` walks control edges, `economic-dependency` walks
judgment-based edges, `both` walks both and is the default because it is the
conservative posture.

**The whole causal chain moves.** Measured on Super Micro Computer, Inc.,
2026-09-21, asked without mitigation:

| basis | members | facilities | commitment | headroom |
|---|---|---|---|---|
| `control` | 2 | 1 | $2.000bn | $12.788bn |
| `both` | 4 | 4 | $2.570bn | $12.218bn |

A different basis gives a different **membership**, therefore a different
**aggregate exposure**, therefore a different **headroom**. A product exposing
only control-based grouping computes a compliant-looking number against an
incomplete group — the *Context Starved* counterfactual this rung refuses.

### The units trap, and why the gate is on the consequence

`bank_capital` is denominated in **thousands of dollars** — the FFIEC Call
Report convention, and legitimate source semantics. Read as dollars:

| reading | Tier 1 | 25 % limit | facilities breaching it single-handedly |
|---|---|---|---|
| raw, as dollars | $0.296bn | **$73,939,500** | **42 of 60** |
| normalized | $295.758bn | **$73.940bn** | 0 |

Three orders of magnitude, and nothing in the output says so. The product
normalizes at the acquisition boundary using a factor **declared in
`artifacts/source-vocabulary.yaml`** and never written in code, does not
rewrite the source table, and serves **both** figures with their units.

**`LEX-G06` does not gate on the conversion constant.** It gates on the
regulatory consequence: the estate carries two engineered proposals with their
own `expected_outcome` labels, and the product has to reproduce them. An
implementation holding the correct factor of 1000 and applying it to the limit
instead of the base still fails — that sabotage was run, and it went red.

### A limit is a percentage of capital OR an absolute amount

Regulation O's limit is **$500,000** — five orders of magnitude below the
percentage limits beside it, and not expressible by a product that assumed
`percentage × capital`. The payload names the **rule form** for every limit,
and the regime is effective-dated **at both ends**: the estate's CRR version
carries an `effectiveTo`, and applying repealed law to a 2026 determination is
refused.

### The freshness asymmetry is disclosed, never resolved

Exposure is intraday. The capital base is a quarterly filing, **147 days old**
at the pinned instant. The product does none of the four things it must not:
it does not pretend capital is intraday, does not age exposure to the capital
date, does not refresh capital to the exposure instant, and mints no fused
timestamp. The denominator's own `report_date` and `age_days` travel **with**
the ratio, and `freshness_asymmetry.resolved` says `false` out loud.

### The determination, end to end

```
  capital    raw 295758000 usd_thousands  ->  $295.758bn usd
             authority: FFIEC Call Report — amounts reported in thousands of dollars
             reported 2026-03-31 · 147 days old at the determination instant

  regime     regime-version-pra-2022 · effective 2022-01-01 · percentage-of-capital
             limit $73.940bn (25.0% of eligible capital)
             cites crr-art-395-2021-12-31#... [resolved=true, hash_available=false]

  CONFLICT   limit `internal-appetite` is priced differently by two internal authorities:
               graph-limit-envelope: 5.0% = $14.788bn
               relational-limit-register: 15.00% = $44.364bn
             selected `graph-limit-envelope` by rule `most-conservative-internal-authority-binds`

  evaluation BINDS FIRST: `internal-appetite` (graph-limit-envelope)
  proposal   $59.400bn · basis assumption (a hypothetical, not evidence)
             regulatory outcome: FITS
```

and the same question with `--no-mitigation`:

```
               regulatory-large-exposure  counted $74.000bn vs $73.940bn breached=true
             regulatory outcome: BREACHES
```

**$60.5 million** — 0.08 % — is the whole margin, and recognizing the undrawn
relief is what crosses it. That is `LEX-G15`: `apply_mitigation` is not a flag
that travels, it is a flag that decides.

## Artifact-by-artifact

| artifact | what it carries |
|---|---|
| `artifacts/source-vocabulary.yaml` | every store, table and URI prefix read; **the declared capital-unit factor and its authority**; **the admissible connection bases** |
| `artifacts/question.yaml` | the three demonstration anchors and the pinned instant, every measured figure they reproduce, the regime set and the two conflicting limit authorities |
| `artifacts/perspectives.yaml` | the three renderings and which members each carries |
| `artifacts/gates.yaml` | the twenty-one declared gates, each with its sabotage and the observation of it going red |
| `ccf_config.yaml` | operator declaration, request contract and argument domains, λ_c per entity class, TTL, debt thresholds, the door's description |
| `ccf_environment.yaml` | every environment variable by name, with the remedy for each |

The code is thin and generic. **An example whose code would still run
meaningfully with its artifacts deleted has violated the No-Hardcoding Rule** —
and one such violation was found and fixed during this build (`LEX-F-07`).

## Whitepaper / CLAUDE.md sections exercised

| section | how |
|---|---|
| Whitepaper §7.4 — operator algebra | Policy → Temporal → Traversal, asserted against this class's own declaration (`LEX-G01`) |
| Whitepaper §7.5 — Projection | one `plan_id`, three renderings branching on `perspective.role` |
| Whitepaper §7.6 — Context Product Contract | `extra=forbid` payload whose member set is a function of the perspective |
| Whitepaper §7.7 — half-life and Context Debt | λ_c per entity class; `compose_debt_factors` under `D-IMPL-104` worst-factor |
| Whitepaper §7.10 — Decision Replay | the examiner's `replay_attribution`, and `policy_bundle_versions` on lineage |
| CLAUDE.md §6.4 — No-Hardcoding | the capital factor and the basis vocabulary are declared artifacts, not code |
| CLAUDE.md §7.1/§7.3 — MCP egress | the standard door with three typed overrides; the closed `proposal` object crosses it byte-identically |
| CLAUDE.md §9 — estate discipline | reads `.76` only; seeds nothing; asserts relationships, never estate counts |

## What to change first

| To change | Edit |
|---|---|
| which stores and tables are read | `artifacts/source-vocabulary.yaml` |
| **the capital unit factor and its authority** | `artifacts/source-vocabulary.yaml` → `capital_units` |
| **which connection bases are admissible** | `artifacts/source-vocabulary.yaml` → `connection_bases`, and the matching `argument_domains` in `ccf_config.yaml` (`LEX-G03` asserts they agree) |
| who sees what | `artifacts/perspectives.yaml` |
| the demonstration anchors and instants | `artifacts/question.yaml` |
| operators, λ_c, TTL, debt thresholds | `ccf_config.yaml` |
| environment variable names | `ccf_environment.yaml` |

### Illustrative calibration

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

Concretely (`D-IMPL-323`): the capital base is a quarterly filing 147 days old
at the pinned instant, so `default_debt_tolerance` is `0.98`. A tighter
tolerance would withhold every answer and demonstrate nothing. The staleness is
not hidden by that choice — it is what forced it, it travels with every ratio,
and it is the subject of `LEX-G14`.

## What would fail

### The source ledger point, and what `unreported` means

This rung reads the ledger position from Fluree's `x-fdb-t` **response
header**, which this deployment does not emit. The payload therefore serves
`ledger_t: "unreported"` **beside** `ledger_point_resolvable: "false"` — the
disclosure is explicit, and `LEX-G21` gates on it rather than on a value.
Nothing is minted: not request time, not ingestion time, and never
`graph_snapshot_at`, which is the CCF snapshot the replay record retains
rather than the source's own position.

`LEX-F-04` concluded the point was unrecoverable from this estate. Measured
2026-09-22, it is recoverable — on `/v1/fluree/ledgers`, a route this rung
does not ask. Returned as a finding; correcting it would change what this
shipped product serves.

Twenty-one declared gates, `LEX-G01`..`LEX-G21`, in
[`artifacts/gates.yaml`](artifacts/gates.yaml). **All twenty-one were observed
RED under their own sabotage** on 2026-09-21 against the live estate; none is
`unavailable`. Four sabotages failed to redden on the first attempt and were
**corrected rather than swapped** — each is recorded as a finding, because each
was a defect in the proof machinery rather than in the product.

What breaks the product, concretely:

- reading the capital base as dollars — both engineered outcomes flip
  (`LEX-G06`);
- pinning `connection_basis`, so a larger group consumes no more of the limit
  (`LEX-G04`);
- ignoring a regime's `effectiveFrom` or `effectiveTo` (`LEX-G05`);
- assuming every limit is `percentage × capital`, which makes Regulation O
  inexpressible (`LEX-G09`);
- dropping either internal limit authority, or choosing between them without
  naming the rule (`LEX-G11`);
- letting a proposal reach the debt factors (`LEX-G19`);
- minting a ledger point this estate cannot resolve (`LEX-G21`).

### What this rung does NOT prove

**Composition.** `Q1` was ruled on 2026-09-21: CP-21 is a **single-class
producer** and builds no child trees. The six prerequisites the source
specification names are re-acquired here. **Composition over children remains a
named coverage gap** and CP-21 was deliberately not enlarged to close it.

**RWA and FFIEC 101 concentration reporting** are out of scope by §0.3, and a
**group registry** does not exist in this estate by design — deriving the group
is the capability under test.

**Rung 23's boundary is preserved** (`PEW-G18`): nothing in
`examples/cp-23-portfolio-early-warning` reads `limit_definition`,
`bank_capital` or a connection basis. Those are this product's inputs, and
nothing here reaches back into rung 23.

The nine findings, including three SDK-adjacent ones and four estate
limitations, are in [`FINDINGS.md`](FINDINGS.md).
