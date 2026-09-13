# Credit Surveillance / Early Warning — what it does, and why it is not a report

A surveillance sweep asks one question: **what changed on this name since we last
looked, and does it matter?** The hard part is not finding the signals. It is
knowing which ones still count.

Every figure below came out of a run against the live estate.

## The argument, in one paragraph

Five kinds of signal reach a credit file, and they expire differently. An adverse
media mention is stale in a week. A spread move is stale in a day. A WARN notice
matters for six months. A financial trend delta for a quarter. And an **8-K
acceleration filing never becomes false at all** — a company that triggered a
covenant in 2024 still triggered it. What ends that filing's relevance is not
time passing; it is **a later filing**. Get that wrong in the obvious direction —
treat "does not decay" as "counts forever" — and 30 of the 50 names in this book
breach the highest escalation band, which is a screen nobody can use. Get it
right and the same machinery puts three names there.

## The pipeline, in three rows

| stage | what happens | where |
|---|---|---|
| **acquire** | two source legs over one delta window. PostgreSQL carries every date; Fluree carries the supersession chain and **no timestamp at all** | `acquisition.py` |
| **assemble** | signals and the obligor into L2, edges first and nodes last; two entity classes so a signal can age without the obligor's identity ageing | `deployment.py` + `ccf_config.yaml` |
| **project** | the delta, the supersession filter, the decayed contributions, the composite, the band, the coverage and **the exclusion list** | `projection.py` |

`produce.py` is the spine — boot, acquire, govern. It contains no gate, no
binder, no debt scorer and no replay record of its own.

## Run 1 — the heavily-signalled name

```
$ make -s example-cp-11
```

Super Micro Computer, over the two years to 2026-08-19.

**139 signals** in the delta. **25 of its 26 8-K filings are superseded and
contribute nothing.** The composite is **0.3134**, which reaches the
**credit-committee-referral** band.

**What a banker should notice.** The exclusion list is the useful half. It says,
for each of those 25 filings, *"a later filing replaced this one; its relevance
ended rather than decayed."* That is the sentence a credit officer needs when
asked why a name with 26 filings scored 0.31 — and it is the difference between a
score and an argument. The question *"why did this not escalate further?"* is
answered by what was left out, never by the total.

**What an engineer should notice.** The estate declares the committee band at
0.55; this product declares it at 0.25, and the payload carries **both**. The
estate's value was calibrated against the accumulating reading — and under it, no
obligor in the book reaches committee at all. A payload showing only the value in
force would hide that a calibration decision was taken.

`D_c` **0.5818**, signal `ok` — `F` 0.6970, `C` 0.6000, `S` 1.0000.

## Run 2 — the thinly-evidenced name

```
$ make -s example-cp-11 LEI=G8NWFN4YP7CR6FOP4886
```

Tupperware Brands. One 8-K Item 2.04 at severity 1.0 — the only item class that
carries it. 23 media mentions. And **zero** XBRL trend deltas.

**The absent class is the finding.** The payload reports `trend_delta: absent`,
not `0`. Those are different statements: one says *"we looked and found nothing
concerning"*, the other says *"we have nothing to look at."* Scoring an absence
as a zero is how a thin file comes to look like a clean one.

Composite **0.0900**, no band. `D_c` **0.8628 · fail_closed**. **A name with
almost no evidence producing high Context Debt and no escalation is the fabric
working.** The product is not saying Tupperware is fine; it is saying it cannot
support a judgement.

## Run 3 — the governed refusal

```
$ make -s example-cp-11 DEBT_TOLERANCE=0.20
```

A caller who declares they will not act on an answer carrying more than 0.20 of
Context Debt gets a **refusal**, returned as data with a replay reference — not
an exception, so a client cannot swallow it in a bare `except`.

## Run 4 — the cross-product case, which is why this rung exists

Not a flag on `run.py`; it is what `EWS-G25` proves.

An acceleration filing lands. The obligor's context moves, and the fabric records
an **invalidation boundary** at the instant the evidence became true in the
world. Then:

| | |
|---|---|
| a product that **read that obligor** at an older snapshot | **refused** on its next serve |
| a product that **did not**, built at the same instant | **still serves** |
| a product **derived after** the filing | **serves** |

**The middle row is the one that matters.** It is exactly as old as the refused
product. A mechanism keyed on elapsed time rather than on what a product actually
read would refuse it too — and would be a global clock wearing an invalidation's
name.

**And the refused product need never have mentioned early warning.** The covenant
product does not know this product exists. It is refused because it read an
entity whose context moved.

## Vocabulary

| term | what it means here |
|---|---|
| **delta** | what is new since the last look. Bounded on the **world's** clock — the signal's own observation date — never on when the fabric ingested it. |
| **superseded** | a later filing replaced this one. Its relevance **ended**; it did not age out. |
| **not-participating** | this signal is in no supersession chain at all. **Not** superseded — there was never a chain to be superseded from. |
| **composite warning score** | a weighted sum of decayed contributions. What the evidence *says*. |
| **Context Debt (`D_c`)** | how old and how complete the evidence *is*. A different model, and the two disagree 36 times across 14 names. |
| **invalidation boundary** | the instant an entity's context changed, after which a product built on older state is no longer eligible to serve. |
| **absent** | this class has no evidence for this obligor. Never a zero. |

## Where each claim is enforced

| claim | enforced by |
|---|---|
| a superseded filing contributes nothing | `EWS-G07` |
| absence from a chain is not supersession | `EWS-G08` |
| the delta is on valid time and admits no look-ahead | `EWS-G10` |
| an absent class is absent, not zero | `EWS-G13` |
| only resolved WARN matches contribute; the rest are counted | `EWS-G14` |
| the exclusion list names a reason per signal | `EWS-G18` |
| no date is parsed out of a label | `EWS-G20` |
| the payload claims no notification, recall or eviction | `EWS-G22` |
| the cross-product case, all three legs | `EWS-G25` |
| a valid SIC never falls silently to `Unclassified` | `EWS-G26` |
| supersession participation is declared, not inferred | `EWS-G27` |
| the three chain states partition | `EWS-G28` |
| the two decay models stay independent | `EWS-G29` |

## Why you can trust these numbers

**All 29 gates were sabotaged.** 25 went red on their own assertion. 3 could not
be falsified from this deployment at all — an SDK guard refuses the bad state
first — and are recorded `unavailable`, never folded into `passed`. 1 has nothing
to range over on this estate and **skips** rather than passing over an empty set.

**Three gates were wrong on the first attempt, and all three are recorded.**
`EWS-G27` stayed green under the sabotage that inferred supersession
participation from the data — because on this estate the inferred answer and the
declared answer are *the same value*. **A gate asserted only where two answers
coincide proves nothing about which one produced them.** `EWS-G29` stayed green
under a sabotage that crossed the two decay models, because structure and
correlation both survived it; only recomputing the arithmetic caught it. And
`EWS-G20` went red against **correct** code, because it searched source text and
tripped on the comment explaining its own rule.

**This rung produced two SDK rulings, and the second was a defect in the first.**
`D-IMPL-334` built serve-time dependency invalidation. It shipped with 14 tests
and 8 sabotages, all green — and still recorded the wrong instant, because every
one of those tests built its claims directly, where the two clocks never
separate. Only a product going through real assembly could see it. `D-IMPL-335`
corrected it: the boundary is when the evidence became true in the world, not
when the fabric happened to write it.

## What these runs do NOT show

- **No notification, no recall, no eviction.** The fabric refuses to **re-serve**
  an obsolete answer. It cannot reach a copy a consumer already holds, and no
  system can. A holder learns by asking again.
- **No delta between two ledger points.** The article asks for one; measured,
  this estate's entire signal population arrives in a single bulk load, so a
  ledger delta returns everything or nothing. The product uses valid time and
  **says so** rather than substituting quietly.
- **No per-mention media sentiment.** `tone` looks like a score and is a query
  filter — all 951 rows carry the same string.
- **No Item 4.02 non-reliance events.** Two obligors have a lifetime count; none
  falls in the window.
- **One cold-start anchor per obligor, all on the same date.** The estate seeds a
  starting point, not a sweep history, so the default delta is the full window.
- **The half-lives and bands are illustrative.** This example runs against a
  point-in-time demonstration estate rather than continuously refreshed
  production data. They are calibrated to make the governed behavior observable
  in that snapshot and should not be read as recommended production values.
