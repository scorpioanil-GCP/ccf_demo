# What a Context Product gives you that a report does not

**Seven questions about one counterparty, asked of one database, at one
instant.** This document records what came back each time, and — the part that
matters — **what a banker relying on an ordinary query or report would have
missed.**

Every figure below came out of a live run against the counterparty estate. None
is illustrative, none is rounded for the slide. The section *"Why you can trust
these numbers"* says how to reproduce them.

---

## The argument in one paragraph

A report tells you **what the data says**. A Context Product tells you **what
you may rely on, who may rely on it, how long it stays good, how complete it
is, and refuses outright rather than guessing** — and it seals each answer so
you can prove, months later, that the number in the credit memo is the number
the system actually produced for that person at that moment.

The seven runs below are seven ways those two things come apart. In five of
them the ordinary tool returns something that **looks like an answer and is
not**.

---

## Six words this document uses

| Term | What it means here |
|---|---|
| **Context Product** | A governed answer to a specific question, not a table or a feed. It carries the data *and* everything you need to rely on it. |
| **Content address** | A tamper-evident seal on one answer — a fingerprint computed over the whole thing. Two answers with the same seal are the same answer; a different seal means something changed. |
| **Context debt (`D_c`)** | A completeness score **on this answer**, from 0.0 to 1.0. Not a data-quality score on a table — a measure of how much this particular question could not be fully answered. |
| **Principal** | Who is asking, and what they are entitled to see. Every answer is scoped to one. |
| **Anchor** | The identifier you asked about — here an LEI, or an internal client number. |
| **Replay record** | The audit trail that lets you reconstruct the answer later: which data, which entitlements, which version of the rules. |

---

## Why you can trust these numbers

Every figure comes from commit **`1f5e9da`**, asking the question **as of
`2026-08-16 12:00 UTC`**, against the live counterparty database.

The test is **same question → same answer.** Not "does it agree with the world
today" — the world moves. A reader who runs this and gets different numbers has
**recalculated, not replayed**, and that distinction is the whole point of the
seal.

To reproduce, from the repository root:

```bash
make venv
export CCF_CP_01_POSTGRES_DSN="dbname=<your database>"
make -s example-cp-01
```

---

## The seven runs at a glance

| # | What was asked | What came back | Completeness | Seal | Stopped? |
|---|---|---|---|---|---|
| 1 | The counterparty | The full record | `0.29` — fine | `ab2e1a62…` | no |
| 2 | The same, by a different person | **Nothing, and no reason given** | `1.00` — **fail closed** | `1f37263d…` | no |
| 3 | A counterparty whose LEI lapsed | Nothing, **and why** | `0.29` — fine | `d22e96ad…` | no |
| 4 | The same, asking for it anyway | The record, flagged `LAPSED` | `0.29` — fine | `a0d5d11c…` | no |
| 5 | An identifier that doesn't exist | **A 404, not an empty record** | — | — | **yes** |
| 6 | "As of last January" | **Refused — this product cannot do that** | — | — | **yes** |
| 7 | A private borrower with no LEI | **Refused — a known defect, documented** | — | — | **yes** |

**Four different seals for the same counterparty, at the same instant.** That is
the single most important line in the table, and the section on the seal says
why it matters to an auditor.

---

## Run 1 — the baseline, and the five things a report leaves out

```bash
make -s example-cp-01
```

The record comes back as you'd expect — AVIS BUDGET GROUP, INC., its LEI, its
legal form, its addresses, its status. **A report would have given you that
much.** Underneath it, the product also returns this:

```
What a plain SELECT would not have told you:
   asked as of        2026-08-16T12:00:00+00:00
   expires at         2026-08-17T00:00:00+00:00   (ttl_anchor from_entity_freshness)
   context debt D_c   0.2929  ->  ok
   identity authority lei-reference-data
   freshness ceiling  1 day(s)   (signal class vendor_identity)
   principal          PRIN-COV-001   sees 10 jurisdiction(s)
   operators invoked  ['policy.principal-subgraph']
   content address    ab2e1a62bf0e5b26c86b3dc122bc77ca4c7e8162ef86510f4a0901224723e9e4
   replay record      5cd4126b9a5eac5009dd1a01e13be27615e60ed75cce086ce2fa16bbf51dd888
```

That is the screen exactly as it prints. In plainer terms:

| It prints | It means |
|---|---|
| `expires at … ttl_anchor from_entity_freshness` | this answer's shelf life, calculated from when the source record was last refreshed |
| `context debt D_c 0.2929 -> ok` | completeness score, and a verdict that it is within tolerance |
| `identity authority lei-reference-data` | which register of truth vouched for this identity |
| `freshness ceiling 1 day(s)` | how stale this class of data is allowed to get |
| `principal … sees 10 jurisdiction(s)` | who asked, and the scope they are entitled to |
| `content address` | the seal on this answer |
| `replay record` | the audit trail that reconstructs the decision |

Line by line, and what each one prevents:

- **`expires at`** — this answer has a shelf life, and it is *calculated from
  when the underlying record was last refreshed*, not set by a fixed policy. A
  report has no expiry. **An analyst pastes a counterparty record into a credit
  memo in March and it is still sitting there, unmarked, in September.**
- **`completeness 0.2929 → ok`** — a *number*, not a green tick. Something is
  imperfect; the product says how much and then says it is within tolerance.
  **You can set a different tolerance for a $5m facility than for a $500m one.**
- **`identity authority`** — *which* register of truth vouched for this
  identity. Here, public LEI reference data. A private borrower resolves through
  a different authority entirely, with different freshness rules (Run 7).
  **When a regulator asks "on whose authority did you believe this was that
  company?", this line is the answer.**
- **`principal … 10 jurisdictions`** — the answer is scoped to who asked. Run 2
  changes nothing but this.
- **`seal` and `replay record`** — the answer is addressable and the decision is
  reconstructible. Neither exists for a query result.

### The detail that is easy to miss

```
legal address          WILMINGTON,  Delaware
headquarters address   Parsippany,  New Jersey
```

Delaware-incorporated, New Jersey-headquartered — an entirely ordinary
structure, and **the distinction is load-bearing.** The entitlement check in Run
2 runs on the **legal** jurisdiction, Delaware. Not the operating headquarters.

**A system that stores one address per counterparty has already made an
access-control error it has no way of detecting.** It will grant or deny on
whichever address happened to get loaded.

---

## Run 2 — the same question, asked by someone else

```bash
make -s example-cp-01 PRINCIPAL=PRIN-KYC-004
```

```json
{
  "counterparty": null,
  "perspective_role": "analyst"
}
```

```
   context debt D_c   1.0000  ->  fail_closed
   principal          PRIN-KYC-004   sees 9 jurisdiction(s)
   content address    1f37263d83a9dfe68532ace42d0071644356ed1be7ae3712a88343edb36d137c
```
*(three lines lifted verbatim from the summary block; the rest is as Run 1)*

This analyst's entitlements cover nine European jurisdictions. The counterparty
is Delaware. **So it was removed from the data this person can see *before* the
answer was assembled** — not filtered out of a result afterwards. The product
did not withhold a record it was holding. It never held one.

> ### What you'd have missed
>
> **A query returns zero rows here. So does a query about a counterparty that
> does not exist. They look identical.**
>
> An analyst sees an empty result and concludes there is no such client — and
> opens a duplicate file, or reports no exposure where exposure exists. That is
> not a hypothetical failure mode; it is the most common one in an entitled
> data estate.
>
> **`completeness 1.0000 → fail closed` is what makes those two answers
> different.** The system is not saying *"nothing matched."* It is saying
> **"I could not see enough to answer you, and I will not pretend
> otherwise."**

### The silence is complete, and that is deliberate

| Field | Entitled analyst | Unentitled analyst |
|---|---|---|
| the counterparty | full record | **nothing** |
| freshness ceiling | `1 day` | **gone** |
| signal class | `vendor_identity` | **gone** |

**Three things disappear, not one.** A system that blanks the name but leaves
the metadata standing has just told an unentitled person what *kind* of thing
they were not allowed to see — and in a bank, the existence of a file is often
the sensitive fact. Suppression that stops at the headline value is not
suppression.

---

## Run 3 — refused, and told exactly why

```bash
make -s example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78
```

```json
{
  "counterparty": null,
  "excluded": {
    "include_lapsed": false,
    "reason": "registration-lapsed"
  },
  "perspective_role": "analyst"
}
```

```
   context debt D_c   0.2929  ->  ok
   content address    d22e96ad9c0285e92e0a5a1577fdcc79a83afd9ba8762ff264a4a04bf90bdd83
```

### Two silences, and only one of them explains itself

Runs 2 and 3 both return nothing. **Run 3 says why; Run 2 refuses to.** That
asymmetry is designed, not accidental:

| | Run 2 — not entitled | Run 3 — lapsed registration |
|---|---|---|
| explanation | **none** | `registration-lapsed` |
| completeness | `1.00` — fail closed | `0.29` — fine |
| why the difference | explaining would leak: *"you may not see it"* confirms it exists | the analyst **is** entitled to it; it was excluded by a setting they may change |

### Completeness measures what could not be seen — not what was withheld

Run 3's completeness is **`0.2929` — identical to the successful Run 1.**
Nothing was stale, nothing was unreachable. The counterparty was found, read,
and then excluded by a rule.

**That is why completeness is a number and not a flag.** A yes/no cannot express
*"I saw everything I needed and returned none of it, on purpose."* An operations
team chasing a data-quality alert needs to know the difference immediately.

### The refusal names its own override

```json
"include_lapsed": false
```

The answer does not merely say *excluded*. It names **the setting that would
change it, and its current value.** Nobody has to find the documentation, raise
a ticket, or ask the vendor.

> ### What you'd have missed
>
> A feed that silently drops lapsed registrations, or silently keeps them.
> Either way you cannot tell from the output which it did. Here the exclusion
> is **visible, explained, and reversible**, and reversing it is recorded.

---

## Run 4 — asking for it anyway, and why the seal changes

```bash
make -s example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78 INCLUDE_LAPSED=1
```

Five fields, excerpted from the full record it returns:

```json
{
  "entity_status": "ACTIVE",
  "headquarters_address": { "city": "Parsippany-Troy Hills", "country": "US", "region": "US-NJ" },
  "legal_address": { "city": "Wilmington", "country": "US", "region": "US-DE" },
  "legal_name": "B&G Foods, Inc.",
  "registration_status": "LAPSED"
}
```

```
   content address    a0d5d11c7881d37d2c4c52197c5d182cdb34155bd15daca9ed5f995136c6354a
```

**Same counterparty, same instant, one setting changed — and the seal moves from
`d22e96ad…` to `a0d5d11c…`.**

### Two status fields that disagree on purpose

```
entity_status:        ACTIVE
registration_status:  LAPSED
```

**B&G Foods is a live, trading company whose LEI registration has lapsed.** Those
are two different facts about two different things: the company, and its
paperwork.

A single "status" column collapses them into one wrong one. Collapse them the
optimistic way and a counterparty with a lapsed identifier flows into trade
reporting that requires an active one. Collapse them the cautious way and you
decline business with a perfectly good client over an administrative lapse.

> ### What you'd have missed
>
> **The record comes back with its lapse stated on its face.** You asked for it,
> you get it, and you are told what you are holding.
>
> The alternative — returning it quietly, indistinguishable from a clean record
> — is how a lapsed registration ends up inside a credit decision, and how
> nobody can later establish whether anyone knew.
>
> And because the seal changed, **the override is evidence.** You can prove
> somebody deliberately asked for the lapsed record rather than receiving it by
> accident. That is the difference between an exception and a defect.

---

## Runs 5 and 6 — the two that stop the process

Both of these **stop rather than return.** That is the correct behaviour, and
each replaces a specific quiet failure.

### An identifier that does not exist

```bash
make -s example-cp-01 ANCHOR=NOSUCHENTITY0000000
```

```
assembly refused: anchor 'NOSUCHENTITY0000000' resolved to no entity through
either identity authority (404); §D.2 step 1 fails closed rather than returning
an empty payload
```

**"No such counterparty" and "a counterparty we hold nothing on" are different
answers.** A system that returns an empty record for both has destroyed the
difference — and onboarding is precisely where that difference decides whether
you open a second file on an existing client.

### A date the product cannot honour

```bash
make -s example-cp-01 AS_OF=2026-01-01T00:00:00+00:00
```

```
assembly refused: 400 not_supported_at_tier: as_of — declared by this class and
always refused (Standard §2.4). This verdict is raised rather than returned
because ProductRequestViolation.reason is a closed Literal with no member for
it; see CP-SPEC-001 §F.4
```

The first sentence is the one that matters to a reader; the second is the
product reporting an SDK limitation against itself, which is covered below.

**The "as of" parameter exists in the contract so you can discover it, and is
always refused so nobody can rely on it in a dispute.**

> ### What you'd have missed
>
> This is the sharpest one for a banking audience.
>
> A system that **accepts an as-of date and quietly ignores it** hands you
> today's data wearing last January's label. The number looks point-in-time. It
> is presented as point-in-time. It is not point-in-time — and there is nothing
> in the output that says so.
>
> Every downstream use of it — a credit review, a year-end position, a
> restatement, an exam response — inherits that error silently, and the person
> who finds it is an examiner rather than an analyst.
>
> **A parameter that silently does nothing is worse than one that does not
> exist.** This product refuses, loudly, every time.

Both stop with a non-zero exit code. **A refusal is not a crash — but it is not
a success either**, and a pipeline should treat it accordingly.

---

## The system never guesses — five ways it says no

| Situation | How it responds | Returned as | Stops? |
|---|---|---|---|
| Not entitled | silence, completeness `1.00` | **an answer** | no |
| Lapsed registration | nothing, plus the reason and the override | **an answer** | no |
| Unknown identifier | `404` | an error | **yes** |
| Unsupported as-of date | refused by contract | an error | **yes** |
| Private borrower, no LEI | freshness gate — **a known defect** | an error | **yes** |

The first two come back as **ordinary answers a system can act on** — a bad
question and a missing counterparty are not broken plumbing, and a downstream
process can branch on them without error handling.

*(Technical note: the split between the two groups is not entirely by design.
The refusal type has no code for "this product does not support that
parameter", so that case has to be raised rather than returned. It is recorded
in the specification's §F.4, which carries eight findings raised by building
this product. They are not uniformly defects — item 7 is a correction to a
mis-reading of the standard — and none of them blocked the build.)*

---

## What the seal is for

| Run | Seal |
|---|---|
| 1 — baseline | `ab2e1a62…` |
| 2 — different person asking | `1f37263d…` |
| 3 — lapsed, excluded | `d22e96ad…` |
| 4 — lapsed, included | `a0d5d11c…` |

The seal is computed over the **entire** answer — the counterparty record, the
entitlements of whoever asked, the completeness score, the expiry, the steps
taken. **One value different anywhere and the seal is different.**

Three consequences, and they are why it is worth computing:

1. **You can prove reproduction in one line.** Compare one value instead of
   diffing two documents. *"Is this the number the system gave us in August?"*
   becomes a yes or a no, not an investigation.
2. **Who asked is auditable, not merely logged.** Run 2 differs from Run 1 by
   the person asking and nothing else — and it is a **different sealed answer**
   with its own audit record, not the same answer with a view over it. When a
   control question is *"what did this analyst actually see?"*, that is the
   thing you can answer.
3. **A setting that changed nothing is detectable.** Run 3 against Run 4 proves
   the override worked: had it been ignored, the two seals would match. **A
   control you cannot see failing is not a control.**

---

## What these runs do **not** show

Stated plainly, because a demonstration that claims everything demonstrates
nothing.

- **No relationship or ownership traversal.** This is the simplest product in
  the catalogue — one database, one counterparty, one entitlement check. Group
  structure, exposure roll-up and collateral coverage are later products.
- **No AI in the path.** Every step here is deterministic. Nothing about these
  runs demonstrates model governance, because there is no model.
- **The counterparty was chosen, not sampled.** It resolves cleanly. These runs
  are not evidence about the overall quality of the underlying data.
- **The summary block printed below the answer is not the answer.** In Run 2,
  underneath the blank record, the demonstration's own printout still shows
  `identity authority` and `signal class` — read from the lookup step, which
  runs *before* the entitlement check. **The governed answer suppresses all
  three fields correctly; this example's console output does not.** Recorded as
  an observation raised, not a defect ratified.

---

## Run 7 — the defect this example documents rather than hides

```bash
make -s example-cp-01 ANCHOR=CLI-000101
```

```
RuntimeError: the three validation gates refused this product: gate='ttl-bounds'
detail='expires_at 2026-02-24T00:00:00+00:00 is outside (now, now + MAX_TTL] =
(2026-08-16T12:00:00+00:00, 2026-08-17T12:00:00+00:00] (INV-CH7-48)'
max_ttl_seconds=86400
```

In plain terms: **this counterparty's data was last refreshed in February, and
the product will not serve anything older than 24 hours.**

`CLI-000101` is a **private borrower with no LEI**. It resolves through the
second identity authority — the internal client master — where freshness is
anchored on the **last KYC refresh** rather than on a public register's
retrieval date.

A KYC refresh is *months* old by design. A 24-hour maximum shelf life is not.
**The two do not compose, and every one of the 30 no-LEI counterparties in the
estate refuses.**

**This is a shipped defect that is documented and tested, not one that slipped
through.** The test asserting it is written so that **it turns red when the
defect is fixed.**

That inversion is deliberate. The test is not ratifying a bug — it is **the
evidence the deviation gets taken back with.** Nobody can quietly declare the
problem solved; the suite says when it actually is.

The freshness anchoring this exposes is the entire subject of the next product
in the catalogue.

---

## The whole thing in one sentence

A query returns rows. **A Context Product returns rows, plus who is entitled to
rely on them, plus how long they stay good, plus how complete the answer is,
plus a seal that proves it reproduces — and it refuses, in five
distinguishable ways, rather than handing you something that merely looks like
an answer.**

---

*Runs captured at commit `1f5e9da`, asked as of 2026-08-16 12:00 UTC.
Specification: `spec/CP-SPEC-001_Counterparty_Reference_Snapshot.md`.
Tests: `tests/examples/test_cp_01_output.py`.*
