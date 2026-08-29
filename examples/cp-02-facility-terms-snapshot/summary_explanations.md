# Facility Terms Snapshot — what it is, and what it is worth

**Audience: a banker, not an engineer.** This document explains what the product
does and why it is worth funding. The README beside it explains how it was
built, to somebody building one.

---

## The argument, in one paragraph

A report tells you what the data says. **A Context Product tells you what you
may rely on** — who may rely on it, how long it stays good, how complete it is,
and it refuses rather than guessing. The difference shows up on the day the
answer is wrong: a report hands you 2021 terms with today's date on the screen
and no way to tell; this product hands you the same terms with an expiry derived
from the agreement's own date, and declines to serve when it cannot vouch for
them. Everything below is a real run against a real store.

## A short glossary

| The term | What it means here |
|---|---|
| **Content address** | A tamper-evident seal on **one answer**. It is a hash over the whole reply, so it only reproduces if every input did — the facility, the entitlements, the completeness score, the expiry. One drifted value anywhere and the seal differs. |
| **Context debt** (`D_c`) | A completeness-and-freshness score **on that answer**, not a data-quality score on a table. Low is good. It is delivered *with* the answer, because a consumer that receives context with no debt signal cannot know what it is trusting. |
| **Principal** | Who is asking, and what they are permitted to see. |
| **TTL / expiry** | How long acting on this answer stays safe. **The whole subject of this product is which event that is measured from.** |
| **Facility** | One credit line — a revolver, a term loan — under one agreement. |

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
