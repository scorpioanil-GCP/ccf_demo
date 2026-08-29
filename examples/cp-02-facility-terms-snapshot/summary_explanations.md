# Facility Terms Snapshot — what it is, what it is worth, and how it works

**Five questions about one credit facility, asked of one database, at one
instant.** This document records what came back, **what an ordinary query or
loan-system screen would have missed**, and **which mechanism produced the
difference.**

**Written for three readers at once.** A credit or lending subject-matter expert
should be able to read the consequence and skip the mechanism; an engineer
should be able to read the mechanism and find the file; a product manager should
be able to read both and know what is real, what is declared, and what is still
open. Each run carries the same three parts in the same order: **the output**,
**what you'd have missed**, and **how it works**.

Every figure below came out of a live run. None is illustrative. *"Why you can
trust these numbers"* says how to reproduce them, and *"Where each claim is
enforced"* maps every claim to the test that fails if it stops being true.

---

## The argument, in one paragraph

A report tells you what the data says. **A Context Product tells you what you
may rely on** — who may rely on it, how long it stays good, how complete it is,
and it refuses rather than guessing. The difference shows up on the day the
answer is wrong: a report hands you 2021 terms with today's date on the screen
and no way to tell; this product hands you the same terms with an expiry derived
from **the agreement's own date**, and declines to serve when it cannot vouch
for them.

**The one-line version of what is new at this rung:** the expiry is a property
of the instrument, not of the request. Ask twice, a fortnight apart, and it does
not move.

## Vocabulary

Each term twice: what it means to somebody reading the answer, and what it is in
the system.

| Term | What it means here | What it is |
|---|---|---|
| **Content address** | A tamper-evident seal on **one answer**. It only reproduces if every input did — the facility, the entitlements, the completeness score, the expiry. | `sha256` over the canonical bytes of the served product, excluding `assembled_at` |
| **Context debt** (`D_c`) | A completeness-and-freshness score **on that answer**, not a data-quality score on a table. Low is good. | `D_c = 1 − (F · C · S)`, multiplicative, so a collapsed dimension forces escalation instead of averaging away |
| **Principal** | Who is asking, and what they are permitted to see. | A row in `ccf_v2.principal` plus its jurisdiction grants; reaches the assembly as `Perspective` |
| **TTL anchor** | Which **event** the shelf life is measured from. The whole subject of this product. | `ttl_anchor: from_entity_freshness`; the basis is named in the payload as `ttl_basis` |
| **Facility** | One credit line — a revolver, a term loan — under one agreement. | The anchor: an internal identifier with **no external registry** behind it |

**The three steps, in the order the fabric runs them.** Every difference between
the runs below comes from one of these:

| Step | What it does | Where |
|---|---|---|
| **Resolve** | turns a facility id into a record, and names the date the expiry will hang off | L2, the single writer |
| **Policy** | substitutes the caller's permissible set *for* the full one | L4, before anything reads graph state |
| **Contract assembly** | computes the expiry and the debt, runs the gates, seals the answer | L6, and it is not an operator |

---

## Run 1 — the ordinary case, and the field a screen cannot show you

```bash
make -s example-cp-02
```

The reply carries the terms a credit officer expects — borrower, type,
commitment, currency, effective and maturity dates, the pricing grid with its
five leverage tiers, the outstanding balance and the internal rating. Then:

```
   asked as of        2026-08-29T12:00:00+00:00
   ttl basis          2026-07-29   (effective_date, the agreement's own date)
   expires at         2026-10-27T00:00:00+00:00   (ttl_anchor from_entity_freshness)
   context debt D_c   0.0396  ->  ok
   content address    708a4a3f1a8486b125fdcbcbb848c3a43ae7cda81066ad3ee832aafe749d8b0c
```

*Five lines lifted from the run's summary block.*

| The line | What a banker reads |
|---|---|
| `ttl basis` | The expiry was measured from **the agreement's own signature date**, and the reply says so rather than leaving you to assume |
| `expires at` | After 27 October, acting on this without re-reading is not safe |
| `context debt D_c 0.0396` | This answer is 96% complete and fresh against its own standard |
| `content address` | Seal this reply, quote it in a memo, and anyone can prove later that it is the answer you were given |

**What you'd have missed.** A loan-system screen shows the same terms and no
expiry. So the officer caches the row — in a spreadsheet, in a memo, in their
head — and keeps reasoning against it. **The lift is not that the fabric is
clever. It is that the ordinary tool has no way to tell you the answer has gone
off, so nobody ever finds out that it did.**

### How it works

`deployment.py::expires_at` is one line: the facility's `effective_date` plus
`declared_ttl_seconds` from `artifacts/ttl.yaml`. **`asked_at` is not a
parameter of that function and cannot be** — which is the whole design, expressed
as a signature rather than as a comment.

The rest of the summary block:

| The line | What produced it |
|---|---|
| `ttl basis` | emitted by `Resolve` as a named date, not left for contract assembly to pick. The estate holds two dates a reader could plausibly believe the expiry uses — the agreement's `effective_date` and the extraction's `retrieved_at` — and they mean entirely different things |
| `context debt D_c 0.0396` | `FreshnessScorer` against the **structural-terms** half-life (~540 days), scored from the claim's `valid_from`. Which of the four half-life classes `F` is taken against is a decision, not an average: scoring against the 1-day balance would report a seven-year-stable object as perpetually stale |
| `amendments 1` | a **count**, and the payload claims no amendment *date* — the estate holds none anywhere, so nothing is asserted that cannot be evidenced |
| `operators invoked` | held to strict equality against what the engine resolved. A declared operator that did not run, or one that ran undeclared, is a refusal in either direction |

## Run 2 — the same facility, seventeen days later

```bash
make -s example-cp-02 ASKED_AT=2026-09-15T23:45:00+00:00
```

```
   asked as of        2026-09-15T23:45:00+00:00
   ttl basis          2026-07-29   (effective_date, the agreement's own date)
   expires at         2026-10-27T00:00:00+00:00   (ttl_anchor from_entity_freshness)
```

**The question moved. The expiry did not.**

**What you'd have missed, and this is the one worth pausing on.** The obvious way
to build an expiry is *"good for 90 days from when you asked."* It is also
wrong, and wrong in a way that costs money quietly: every time anyone asks, the
clock resets, so a facility whose agreement has not been touched since 2021 looks
freshly validated every single morning. **A staleness control that resets on
being read is not a control.** Here the expiry belongs to the instrument, so
asking about it more often does not make it any more current.

### How it works

Nothing here is a cache setting. `expires_at` is derived once, from a filed
date, and the derivation has no access to the clock. The seal *does* change
between the two runs — the request's temporal boundary is part of the answer —
which is why the gate asserting this compares **expiries** rather than seals. An
assertion that both must be equal would be false; one that both must differ
would be false too.

**Why the alternative was rejected, in one measurement.** Anchoring on
`retrieved_at` — when the extraction ran — makes every facility serve. That
column carries **one distinct value across all 60 rows**, so every facility
would expire at the same instant: a product-level TTL, behaviorally
indistinguishable from measuring off the request. The number that settles it is
1, not 60.

## Run 3 — a facility the product refuses to serve

```bash
make -s example-cp-02 FACILITY=FAC-1FF50C
```

This facility carries **eleven amendments**. Its agreement was signed on
2026-05-29 — outside the 90-day window. The product declines:

```
gate='ttl-bounds' detail='expires_at 2026-08-27T00:00:00+00:00 is outside (now, now + MAX_TTL] = (2026-08-29T12:00:00+00:00, 2026-11-27T12:00:00+00:00] (INV-CH7-48)'
```

*One line, lifted from the refusal.* The command exits non-zero, which is
correct: a refusal is not a crash, but it is not a success either.

**What you'd have missed.** Eleven amendments, and this bank's records contain
**no date for any of them** — the amendment filings were never mapped to the
facilities they amend. So nothing can establish that the terms on file are the
terms in force. A screen would have shown the 2026-05-29 terms with no caveat at
all. **The lift is a refusal you can act on instead of an answer you cannot
audit** — and the honest scale of it: at this instant, **50 of the 60 facilities
in this estate refuse**, and all 43 that carry an amendment history are among
them. That is a finding about the bank's data, surfaced by the product rather
than absorbed by it.

### How it works

`gates.py::_refuse_ttl` requires `now < expires_at <= now + MAX_TTL`, both
bounds from `artifacts/ttl.yaml`. This facility's agreement is older than the
window, so the lower bound rejects.

**The declaration was not widened to make this go away.** Both the 90-day window
and the anchor are the specification's terms; changing either to improve the
demonstration would be adjusting the measurement to fit the result. So the
number stands, the run produces the refusal, and gate `FTS-G09` asserts it —
**written so that it turns RED when the declaration is corrected.** That
inversion is deliberate: the test is not ratifying a defect, it is the evidence
the deviation gets taken back with, and nobody can quietly declare the problem
solved.

## Run 4 — terms that cannot be arithmetic

```bash
make -s example-cp-02 FACILITY=FAC-66B83D
```

```
    "borrower_legal_name": "AVIS BUDGET GROUP, INC.",
    "effective_date": "2026-06-29",
    "maturity_date": "2025-12-15",
    "tenor_days": "NOT_EVALUABLE",
```

*Four fields lifted from the reply.*

The maturity date **precedes** the effective date by 196 days. The product
serves both dates exactly as filed, and refuses to compute the tenor.

**What you'd have missed.** A tenor is a subtraction, and a subtraction always
returns something. A report would have shown **−196 days**, or `-0.5 years`, or
silently sorted this facility into the shortest-dated bucket of a maturity
ladder. **The lift is that a number which cannot be true is never presented as
though it were** — and that four facilities, all extracted from the same filing,
are flagged as one extraction problem rather than four independent oddities.

### How it works

`tenor_days` is the only **derived** field in the payload, and the only one that
could report arithmetic as a term. `_tenor_days` returns `None` for two
different findings that share one representation — an absent maturity date
(7 facilities) and an inverted pair (4) — and the payload distinguishes them
while the score does not, because `D_c` is one dimension and the notice is where
the difference belongs.

Both dates are still served exactly as filed. **Repairing them was available and
refused**: an invented maturity would enter a payload that claims `public`
provenance on that field, which is worse than an unusable claim, because it
looks answered.

## Run 5 — a question that is refused without telling you why

```bash
make -s example-cp-02 PRINCIPAL=PRIN-RES-002
```

This principal is granted every jurisdiction in the estate and holds **no
facility-level need-to-know**. The reply:

```
assembly refused: facility 'FAC-36D0CC' is not available (404); §D.2 fails closed rather than returning an empty payload. A facility_id has no external registry behind it, so an empty payload would read as 'this facility has no terms'
```

That is **the same sentence, to the byte**, that a request for a facility which
does not exist returns.

**What you'd have missed.** The natural message is *"you are not entitled to see
this facility."* It is also a disclosure: it confirms the facility **exists**.
Someone without permission could walk a list of identifiers and learn which ones
are real — the client list, recovered one refusal at a time. **The lift is that
'no' and 'not for you' are indistinguishable to the caller**, while the audit
record still holds exactly which principal asked and what was withheld.

### How it works

One shared function, `assembler.py::_not_available`, produces both refusals —
because the suppression rule is a statement about what a caller can
**distinguish**, and two separately-worded messages drift apart the moment
either is edited.

**This was a defect in the first build, and the run is what found it.** A
suppressed facility returned `200` with `facility: null` while a missing one
raised `404`. The payload carried no marker of what was withheld — and the
**status** carried it instead, which is the same disclosure arriving through a
channel the rule never named.

The two policy conditions compose in one place: the deployment computes the
permitted set as the principal's expanded jurisdiction grants **if** the
principal carries facility-level need-to-know, and the **empty tuple** if it does
not. So the suppression case is reached *through* the shipped operator rather
than around it — and gate `FTS-G03` exists because a two-condition policy where
one condition is inert passes every set-difference check.

## Why you can trust these numbers

Every figure above came from a run, and the run reproduces. The published
transcript was produced against the estate as loaded on **2026-08-25**, asking
as of a pinned **2026-08-29T12:00:00+00:00**, with content address
`708a4a3f1a8486b125fdcbcbb848c3a43ae7cda81066ad3ee832aafe749d8b0c`. Anyone with
read access can re-run the command in the README and compare that address; if it
matches, they have the same answer, not a similar one.

The product's own checks are stronger than its documentation. Eleven of them
were **deliberately broken one at a time** to confirm each actually fails when
its subject is wrong — a check nobody has seen fail is not evidence that it runs.

## Where each claim is enforced

Every claim above is held up by a test that fails if it stops being true. This is
the table to read if the question is *"what stops this from regressing?"*

| The claim | The mechanism | The gate |
|---|---|---|
| The expiry does not move with the question | `expires_at` takes no request parameter | `FTS-G01` |
| Entitlement discriminates, as sets rather than sizes | `PolicyFilter` substitutes the permissible set at L4 | `FTS-G02`, with a negative control |
| Need-to-know does real work, not just jurisdiction | the two conditions compose into one allowlist | `FTS-G03` — removes the condition and requires the served set to change |
| Withheld and absent are indistinguishable | one shared refusal string | `FTS-G04` |
| `as_of` is refused, never silently honored | `unsupported_arguments:` in `ccf_config.yaml` | `FTS-G05` |
| No document pointer reaches the payload | the offsets are never read into the graph | `FTS-G06` — with a control asserting the columns **are** populated, so the gate is not proving that nothing leaked from a column that does not exist |
| The pricing grid is a tier structure, never a scalar | served as `basis` + a tier list | `FTS-G07` |
| An impossible tenor is withheld, not computed | `NOT_EVALUABLE`, never a negative number | `FTS-G08` |
| Terms older than the window are refused | `_refuse_ttl` | `FTS-G09` — **written to go RED when the declaration is corrected** |

**Eleven gates were deliberately broken one at a time and observed to fail**
before any of them was trusted. A check nobody has seen fail is not evidence that
it runs.

Two of those sabotages are worth naming. `FTS-G01`'s — repointing the expiry at
the clock — **passes every other test in the module** and fails only that one,
which is why it exists. And `FTS-G09`'s sabotage is *fixing* the defect, which
correctly turned it red.

---

## What these runs do NOT show

- **They are not a claim about any real company's borrowings.** The filed terms
  come from public credit agreements; the balances, availabilities, internal
  ratings and pricing margins are engineered for demonstration. No number here
  describes a real loan book.
- **No history.** This product answers *what are the terms now*. Reconstructing
  the terms as they stood on a past date needs capability that arrives later in
  the catalog, and asking for it here is refused explicitly rather than answered
  approximately.
- **No covenants, no collateral, no exposure aggregation, no syndicate detail.**
  Each belongs to a different product and each is deliberately out of scope.
- **The freshness figures are not calibrated.** The decay rates are expert
  judgment, not measurement, and the specification says so on every row. They
  are values an engineer can challenge rather than numbers anyone should assume
  were derived.
- **The 50-of-60 refusal rate is a property of this data**, not a prediction
  about a real portfolio. What generalizes is the shape: where amendment dates
  are not captured, currency cannot be established, and a fabric that says so is
  more useful than one that does not.

Where regulatory framing matters — trade reporting regimes that require an
active identifier, or supervisory expectations on model and data lineage — this
document deliberately stays general rather than citing a rule number that has
not been verified.

---

## The whole thing in one sentence

A loan-system screen returns terms. **A Context Product returns the same terms,
plus who may rely on them, plus an expiry measured from the agreement rather
than from the question, plus how complete the answer is, plus a seal that proves
it reproduces — and it refuses, indistinguishably, rather than confirming what a
caller is not entitled to know.**

And the engineering claim underneath it: **none of that is written in code.** The
window is an artifact, the four half-lives are an artifact, the entitlements are
a table, the operator plan is a document carrying a witness per step. What ships
in `/src` is the machinery that interprets them — which is why this product and
the one before it share a fabric without a line of it changing between them.
