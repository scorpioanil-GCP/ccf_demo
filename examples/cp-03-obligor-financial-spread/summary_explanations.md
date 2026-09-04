# Obligor Financial Spread — what it is, what it costs you not to have it

**The argument, in one paragraph.** A report tells you what the data says. A
Context Product tells you what you may *rely on*: who may rely on it, how long
it stays good, how complete it is, which filing asserted each figure — and it
**refuses rather than guessing** when it cannot answer. The difference is not
presentation. A report that is silently stale looks exactly like a report that
is current; a Context Product that is stale says so, and can be made to prove it.

**What is new at this rung, in one line.** Rungs 01 and 02 carry one freshness
for the whole answer. **A spread cannot** — it is stitched from many filings, so
freshness becomes a property of each figure rather than of the document.

---

## The pipeline, in three rows

Every difference between the runs below comes from one of these three. Naming
them once means each run's mechanism note can stay short.

| Step | What it does | Layer |
|---|---|---|
| **Resolve** | turns the obligor's LEI into this estate's internal identity, **through rung 01's crosswalk** — never through the fact table's own company number, which would make this product its own system of record for identity | L2, assembly |
| **Policy** | filters the graph to what the *asking principal* is entitled to see. The only operator in the plan, and an empty plan is refused, so the product cannot serve without it | L4, operator |
| **Contract assembly** | builds the typed answer, computes the expiry and the debt figure, seals it with a content address, and writes the replay record | L5–L6 |

---

## Run 1 — the default question

### The output

```
make -s example-cp-03
```

Excerpt — the closing summary. The full run also prints the spread itself, 16
columns of figures, each naming its own filing.

```
What a plain SELECT would not have told you:
   asked as of        2026-08-29T12:00:00+00:00
   basis applied      as-reported   (both settings are correct; the decision picks)
   period ends asked  8   -> 8 returned, 16 columns
   decay rates        ['annual_facts', 'quarterly_facts']   ...ONE product, 2 half-life class(es) — §E.1
   latest filing      2026-08-05   (the TTL anchor, and it MOVES as the obligor files)
   expires at         2026-09-04T00:00:00+00:00   (ttl_anchor from_entity_freshness)
   restated lines     ['equity', 'interest_expense']
   formally restated  True   (an Item 4.02 exists — CORROBORATION, never the detector)
   context debt D_c   0.8782  ->  fail_closed
   ...decomposed      F=0.2972  C=0.4097  S=1   (S cannot move: one store, §E.2)
   principal          PRIN-COV-001   10 jurisdiction(s) granted
   operators invoked  ['policy.principal-subgraph']
   policy version     ['f7d293f3fc01775bb8958dca019fb29709b213deab819e7638e3df24021ce3da']
   content address    e2a0224fa5c9ecf4cbf7c0e6ef4ae89a4bccb85d85ebf20f7e206f73b1372edc
   replay record      ad70fa4b511065d7ba436f3d1f9a7ebf20db7951af665fd0a18973853a33b236
```

### What you'd have missed

**Two of these figures were corrected after they were first published, and a
spreadsheet would not have told you which.** `equity` and `interest_expense`
carry more than one value across the filings that reported them. An analyst
pulling this obligor's history into a model gets the numbers either way — but
only one of the two versions is the one the obligor now stands behind, and
nothing in a plain extract says which figure moved.

**You asked for eight periods and received sixteen columns.** This obligor's
financial year ends in March, so one period end carries both an annual cell and
a quarterly cell. A spread built on the assumption of one column per period
would have silently dropped half of them, or double-counted, and the arithmetic
would still have balanced.

### How it works

The restatement is found by comparing values across filings on the estate's own
fact-identity key, declared in **`artifacts/restatement.yaml`** — not by looking
for a regulatory notice. The key is in an artifact rather than in code because
"what counts as the same fact" is a credit-policy judgment wearing numeric
clothing. Gate **`OFS-G03`** fails if the key is relaxed; gate **`OFS-G01`**
fails if the payload loses its balance-sheet half.

---

## Run 2 — the same obligor, read the other way

### The output

```
make -s example-cp-03 BASIS=latest-restated
```

Excerpt — only the lines that differ from Run 1 are shown.

```
   basis applied      latest-restated   (both settings are correct; the decision picks)
   context debt D_c   0.8311  ->  fail_closed
   ...decomposed      F=0.4122  C=0.4097  S=1   (S cannot move: one store, §E.2)
   content address    9fe28bb16cfa0fa035bcd0099a177ef5d66152398af3f84ed6f662a7bfa61011
   replay record      2dec0385f1afdd52b2f9397cc54ae1a203f459bd7f1e630e0e132eedd1d16a8c
```

### What you'd have missed

**These are two different answers, and both are correct.** `as-reported` is what
the obligor said at the time — the right basis for asking *what did we know when
we approved this facility?* `latest-restated` is what the obligor says now — the
right basis for *what is true today?* Neither is the truth; the decision picks.

**The consequence is a cache.** The two answers have different seals
(`e2a0224f…` and `9fe28bb1…`), so a system that stores answers can never hand
one back for the other. Without that, a covenant test run on an *as-reported*
basis could quietly be served a *restated* answer from cache, and the breach
would appear or disappear with nothing in the record showing why.

### How it works

`basis` is a request parameter, and it travels into the content address. Gate
**`OFS-G11`** asserts the *figures* move for an obligor carrying a restatement —
not merely that the seal changed, which an earlier version of the gate did and
which proved nothing.

---

## Run 3 — the full ratio block

### The output

```
make -s example-cp-03 LEI=549300FHJQTDPPN41627
```

Excerpt.

```
   period ends asked  8   -> 8 returned, 13 columns
   restated lines     ['assets', 'equity', 'net_income', 'operating_income', 'revenue']
   formally restated  False   (no Item 4.02 — CORROBORATION, never the detector)
   context debt D_c   0.8157  ->  fail_closed
   content address    83e143396f512b947c41582318f1cba356acd5dfad8edbf83295d94c469b242e
```

### What you'd have missed

**Five spread lines were restated and the obligor filed no non-reliance notice
at all.** This is the case that breaks the obvious approach. An Item 4.02 is the
regulatory filing that says *do not rely on our previously issued statements* —
the natural place to look for restatements, and the wrong place to look *from*.
**Twenty-eight of the 37 restated obligors in this estate filed none.** A
monitoring process keyed on 4.02 filings would report a clean book and miss
three quarters of the corrections.

**And the reverse case exists too.** Two obligors filed a 4.02 and moved no
figure in the window. Keyed on the filing, they would be flagged as restated,
and an analyst would spend a morning looking for a change that is not there.

### How it works

Detection is declared as `distinct_value_across_accessions` in
**`artifacts/restatement.yaml`**. The 4.02 count is carried as corroboration on
the obligor record and never consulted to decide. Gate **`OFS-G04`** serves the
obligor that filed a 4.02 without moving a figure and fails if any line comes
back marked restated.

---

## Run 4 — the peer cohort

### The output

```
make -s example-cp-03 LEI=529900VKCYZW8GZ4WW58
```

Excerpt.

```
   latest filing      2026-08-06   (the TTL anchor, and it MOVES as the obligor files)
   expires at         2026-09-05T00:00:00+00:00   (ttl_anchor from_entity_freshness)
   restated lines     ['operating_income', 'operating_lease_noncurrent', 'revenue']
   content address    7ca0657af18af4196ebe5fd792e9936be36d26d84e23d637e63a81b61317f944
```

### What you'd have missed

**The peers are joined on the period end, never on the filing date.** This is
the classic spreading error: two companies file in the same week, so their
figures land side by side in a comparison — but one is reporting its third
quarter and the other its second. The comparison looks sound and is meaningless.
Here the join key forecloses it, so a peer figure can only ever be compared
against the anchor's figure for the *same period*.

**Twenty of the 50 obligors have no peer cohort at all**, and they are served
`NOT_EVALUABLE` rather than an empty comparison. An empty cohort presented as a
comparison would read as *this company has no peers worth noting*, which is a
claim about the market rather than about the estate.

### How it works

The cohort is drawn by industry classification and the comparison is joined on
`period_end` in **`deployment.py`**. The absence vocabulary is declared in
**`artifacts/expected.yaml`**.

---

## Run 5 — the debt figure, and why it is advisory

### The output

```
make -s example-cp-03 PERIODS=1
```

Excerpt.

```
   period ends asked  1   -> 1 returned, 1 columns
   decay rates        ['quarterly_facts']   ...ONE product, 1 half-life class(es) — §E.1
   restated lines     none in this window
   context debt D_c   0.4940  ->  ok
   ...decomposed      F=0.8280  C=0.6111  S=1   (S cannot move: one store, §E.2)
```

### What you'd have missed

**The same obligor reads `fail_closed` over eight periods and `ok` over one.**
Nothing about the company changed between those two runs. The debt figure is
driven by the **width of the history window**, because freshness composes across
every period and a spread exists precisely to carry old ones.

**This is the number a governance committee would have misread.** Presented as
"data quality," `0.8782 → fail_closed` reads as a problem with the obligor. It
is not. It is the arithmetic of asking for two years of history, and a product
that refused on it would refuse every spread ever requested.

### How it works

The signal is **advisory at every rung of this ladder** and the product serves
the full spread beside it. That is a recorded decision, not an oversight —
`CP-SPEC-003` §F.4 finding 15 carries it, unclosed. The two decay rates in the
default run are the mechanism: an annual column ages against a roughly
365-day half-life and a quarterly column against roughly 90 days, so one payload
carries two decay classes, which a single product-level rate could not express.

---

## Run 6 — the two refusals

### The output

```
make -s example-cp-03 AS_OF=2026-03-31
```

```
refused: not-supported-at-tier — as_of
   as_of: 400 not_supported_at_tier — reconstructing the spread as it stood on a past date requires ledger time-travel and arrives at Tier 3 with covenant-in-force-as-of. This tier serves the spread as it stands, with every figure naming the filing that asserted it.
```

The first line is the SDK's verdict, returned as data by the tier step of
`refuse_request` before the product's own code runs; the second is the detail
the class declaration carries for the parameter, printed beneath it.

```
make -s example-cp-03 PRINCIPAL=PRIN-KYC-004
```

```
assembly refused: obligor '549300D0WZR1VI2QGB24' is not available (404); §D.2 fails closed rather than returning an empty payload. A spread with no lines would read as 'this company reported no financials', which is a claim about the world rather than about the request
```

Both exit non-zero. A refusal is not a crash, but it is also not a success.

### What you'd have missed

**The dangerous outcome of an as-of date is not the refusal — it is acceptance.**
A system that takes `as_of=2026-03-31`, ignores it, and returns today's spread
has answered a question about today while the caller believes they asked about
last March. Every downstream number inherits the wrong date and nothing in the
output says so. This product declares the parameter and always refuses it, so
the caller finds out at the moment of asking rather than at the audit.

**The entitlement refusal is deliberately indistinguishable from absence.**
`PRIN-KYC-004` holds nine jurisdiction grants; none reaches any obligor in this
estate. It receives exactly what it would receive for a company that does not
exist. A refusal that said *"you are not permitted to see this"* would confirm to
an unentitled caller that the obligor is real — which in a bank with information
barriers is the leak, not the protection.

### How it works

The refused parameter is declared in **`ccf_config.yaml`**, not listed in code,
so withdrawing or adding one is a change to that document. Gates **`OFS-G06`**
and **`OFS-G15`** cover the two refusals; `OFS-G15` pairs its negative controls
with a positive one, because a principal that saw nothing would otherwise be
satisfied by an implementation that showed nothing to anybody.

---

## Vocabulary — what the term means, and what it is

| Term | What it means to you | What it is in the system |
|---|---|---|
| **Content address** | a tamper-evident seal on one answer | `sha256` over the canonical bytes of the served product |
| **Context debt** (`D_c`) | how far short of ideal this answer falls | a composite of freshness, completeness and source coverage, `0`–`1` |
| **Half-life** (`λ_c`) | how fast a figure of this kind goes stale | a per-signal-class decay rate; annual and quarterly figures carry different ones |
| **Basis** | which version of history you asked for | a request parameter that selects the filing whose value wins, and travels into the content address |
| **Restated** | this figure was corrected after first publication | more than one distinct value across filings on the fact-identity key |
| **Principal** | who is asking | an entitlement identity whose jurisdiction grants filter the graph before assembly |
| **Replay record** | the receipt that lets you reconstruct this decision | the five-dimension record addressed beside the product |
| **`NOT_EVALUABLE`** | we cannot answer this, and we will not guess | the declared absence token, served wherever a figure is unavailable — never `0` |

---

## Where each claim is enforced

This is the section that separates a demonstration from a guarantee.

| Claim | Mechanism | Gate that fails if it stops being true |
|---|---|---|
| Identity comes from rung 01, not from this product | resolution through the crosswalk | `OFS-G02` |
| A restatement is found by comparing values, not by reading a filing | `artifacts/restatement.yaml` | `OFS-G03`, `OFS-G04` |
| One store is opened and no pre-computed spread is read | store binding in `backends.yaml` | `OFS-G05` |
| An as-of date is refused, never silently ignored | request contract in `ccf_config.yaml` | `OFS-G06` |
| No model is reachable from any step | Assembly Mode 1 | `OFS-G07` |
| Absence is a word, never a zero | declared absence token | `OFS-G08` |
| The expiry follows the newest filing, not the question | `artifacts/ttl.yaml` | `OFS-G09` |
| Entitlement is applied and is not decoration | the Policy operator | `OFS-G10`, `OFS-G15` |
| Both bases are separately addressable | `basis` in the content address | `OFS-G11` |
| Every computed ratio names the figures it consumed | per-attribute lineage | `OFS-G12` |
| Materiality is your policy, not our constant | `artifacts/restatement.yaml` | `OFS-G13` |

**All fourteen gates have been made to fail deliberately at least once**, and
the sabotage applied to each is recorded with its observed result. Three of them
passed their first sabotage and had to be rewritten — a gate that has never been
observed failing is not evidence that it runs.

---

## Why you can trust these numbers

Every figure in this document came from a real run against a live estate on
2026-08-31, not from a design document.

The default run is pinned: `asked_at 2026-08-29T12:00:00+00:00`, serving content
address `e2a0224fa5c9ecf4cbf7c0e6ef4ae89a4bccb85d85ebf20f7e206f73b1372edc`. It
reproduces byte-for-byte on re-running, and the content address is the check
worth making — it is a hash over the entire answer, so it only reproduces if
every input did: the resolved identity, the entitlements in force, the debt
figure, the expiry window and the operator plan. One drifted value anywhere and
the hash differs.

Reproduce it yourself with `make -s example-cp-03`, after setting the connection
string as the README describes.

---

## What these runs do not show

- **A complete spread block on the anchor.** Digital Turbine files no
  depreciation, so EBITDA and its three dependents are permanently
  `NOT_EVALUABLE` in Run 1. Run 3 is the obligor that has them.
- **Reconstruction as of a past date.** Refused here by design; it arrives at
  Tier 3 with a different product.
- **Multiple stores.** This rung reads one. Ledger-held policy versions and
  document-level lineage arrive at later rungs.
- **Two readings of the same company that are the same answer but not the same
  document.** For a company with no restated figures, asking both ways moves
  **no figure at all** — and still produces two different seals. The two
  readings genuinely consult different filings (20 of 75 figures come from a
  different document under each) and report the same number from each. The
  specification originally required the seals to match; that was amended
  2026-08-31, because making them match would have meant hiding which filing a
  figure came from whenever the number happened to agree. At a rung whose
  subject is exactly that, the seal is right to differ.
- **Anything about the obligors themselves.** This estate is public filing data
  used to exercise mechanism. Nothing here is a credit opinion.
