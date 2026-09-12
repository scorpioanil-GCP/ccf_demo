# Treasury Liquidity Position — what it does, and why it is not a report

**Audience: technical product managers, engineers, and banking subject-matter
experts.** Each run below gives you the program's exact output, the business
consequence, and the mechanism — named down to the file, so any claim here can
be checked.

## The argument, in one paragraph

A report tells you what the data says. A Context Product tells you what you may
rely on, who may rely on it, how long it stays good, how complete it is, and
refuses rather than guessing. **What is new at this rung:** one decision instant
governs an answer built from four different kinds of time — a market
observation, a policy effective date, a filed reporting period, and a holding
whose observation time nobody ever recorded — without pretending they are the
same kind of thing.

## The pipeline, in three rows

Every difference between the runs comes from one of these.

| step | what it does | layer |
| --- | --- | --- |
| **Resolve** | turns an LEI into this client, its mandate, its holdings and its counterparties | L2 → L3 |
| **Policy** | selects the regulatory posture **in force at the decision instant**, and emits the version | L4, before anything is measured |
| **Contract assembly** | computes liquidity, duration and concentration; attaches the freshness claim, the debt figure and the content address | L6 |

---

## Run 1 — the live position

```bash
make -s example-cp-09
```

**The output** (excerpt — the liquidity and concentration blocks):

```
American Healthcare REIT, Inc.  ·  mandate MND-001  ·  home USD

LIQUIDITY
  EUR   2 accounts         73966641.14  ->         85749527.07
  GBP   1 accounts         75057537.96  ->        100577100.87
  JPY   2 accounts        136550970.61  ->           852271.69
  USD   4 accounts        165388122.30  ->        165388122.30
                                       total        352567021.93

CONCENTRATION
  breach          30.21%  of limit   30.2   SUBURBAN PROPANE PARTNERS LP
  limit-unknown   17.08%  of limit      —   Peakstone Realty Trust
```

**What you'd have missed.** A treasury dashboard would show one breach and six
counterparties inside their limits. It is not true. **Three of the seven have no
limit on file at all** — and one of those three is a larger exposure than two of
the limits that do exist. The ordinary tool reports a compliant client because
it has no way to say *"I could not check."* This one reports one breach, three
within limit, three **not evaluable**, and publishes the coverage: four of
seven.

**How it works.** `projection.py::_concentration` returns a three-valued
verdict and a coverage ratio. `TLP-G12` fails if the three verdicts stop being
distinguishable; `TLP-G13` fails if the ratio stops agreeing with the verdicts
beside it.

---

## Run 2 — the same question, two days earlier

```bash
make -s example-cp-09 AS_OF=2026-06-15T18:05:00+00:00
```

**The output** (excerpt — the posture block):

```
REGULATORY POSTURE IN FORCE
  FR     standard           effective 2024-01-02   posture-FR-reserve-buffer-v1
  US-NY  standard           effective 2024-01-02   posture-US-NY-reserve-buffer-v1
```

Run 1, at the later instant, reads `enhanced-scrutiny` / `…-v2` / effective
`2026-06-16`.

**What you'd have missed.** Reconstruct a June decision today and almost every
system will apply **today's** policy to it. The client was under standard
scrutiny when the position was taken; a system that shows enhanced scrutiny has
quietly rewritten the past, and the memo built on it will defend a decision
nobody made. Here the two runs return different posture versions and different
content addresses.

**How it works.** `acquisition.py::posture_overlay` selects the latest version
whose `validFrom` is at or before the decision instant — never the ledger head.
`TLP-G09` and `TLP-G10` both fail if that comparison is removed.

---

## Run 3 — the refusal

```bash
make -s example-cp-09 AS_OF=2026-08-21T16:00:00+00:00 CURRENCIES=USD
```

**The output, in full** (the `replay` line wraps here; it is one line):

```
asked        2549004GGE2APGNT6O92 · reserve-buffer · as of 2026-08-21T16:00:00+00:00

REFUSED      product-invariant-refusal
  reason     TLP-G07.staleness
  detail     an invariant the product class declares does not hold for this product

  The determination is preserved in the replay record; the
  consumer envelope discloses less than the fabric recorded.
  replay     ccf-artifact://cp-09-treasury-demo/ccf.replay-record/ac913501824ae99fc215bc00fa583d4c7f89755f750f49b31547458fb6856282@d1178cecdf93a5006e74605f36841b31d84ce7ce2fc870a97a609892947b0f55
```

The command exits non-zero. That is correct: a refusal is not a crash, and it is
not a success either.

**What you'd have missed.** One rate signal was 45 minutes old against a
15-minute requirement. A system that substitutes the last good value produces a
confident number, and the substitution is invisible — nothing looks wrong.
**A treasury product that quietly serves yesterday's curve is more dangerous
than one that refuses**, because a refusal gets escalated and a stale number
gets traded on.

Two details that make this honest rather than lucky:

- **The June rate feed does not cover August**, so it is reported *absent* — not
  as a 59-day-old observation. That age would have been an artifact of the
  query, and it would have masked the real breach.
- **A USD-only request on a USD-home client needs no currency conversion**, so
  no FX rate participates and no FX staleness bound can fire. Scope decides what
  takes part before freshness decides what is admitted.

**How it works.** `deployment.py::build_staleness_gate` supplies the predicate;
the SDK stamps the gate's identity and mints the refusal. The determination —
`SIG-000`, 2700 seconds, against a bound of 900 — is written to the replay
record. `TLP-G07` reads it there; `TLP-G22` fails if an out-of-window feed is
allowed to participate.

---

## Vocabulary

| term | what it means to you | what it is in the system |
| --- | --- | --- |
| Content address | a tamper-evident seal on one answer | `sha256` over the canonical bytes of the served product |
| Context Debt (`D_c`) | how much of the answer the fabric could not stand behind | `1 − (F · C · S)`: freshness, completeness, semantic consistency, multiplied |
| Half-life (`λ_c`) | how fast a signal stops being worth relying on | a decay rate per observation class, in the Control Plane |
| `decay_basis` | *which* clock a signal ages against | `observed-at` (when the fabric learned it) or `valid-from` (when the source saw it) |
| Effectivity | when a rule started applying | `validFrom` on the posture; selected by comparison, never decayed |
| Reporting-period end | the quarter a filed figure closes | a label on a window, not an instant — never aged as an observation |
| Unobserved holding | a balance nobody timestamped | `valid_from is None`, preserved rather than filled in |
| Replay record | the audit trail that can reproduce the answer | five dimensions, written at serve time, addressed by content |

## Where each claim is enforced

| claim | mechanism | gate that fails if it stops being true |
| --- | --- | --- |
| One `as_of` governs the determination | `ProductRequest.asked_at`, supplied by the caller | `TLP-G03`, `TLP-G19` |
| Four kinds of time stay apart | `projection.py` — every element declares a `temporal_class` | `TLP-G14` |
| No timestamp is invented for a holding | `deployment.py` sends `observed_time=None`; the SDK preserves it | `TLP-G15` |
| Policy is selected by effectivity | `acquisition.py::posture_overlay` | `TLP-G09`, `TLP-G10` |
| An out-of-window feed is absent | `artifacts/signal-sources.yaml` declares each window | `TLP-G22` |
| Scope precedes freshness | `currencies` narrows holdings, so FX may not participate | `TLP-G20` |
| "No breach" is not "compliant" | three verdicts plus a published ratio | `TLP-G12`, `TLP-G13` |
| A stale mandatory signal refuses | the declared product gate | `TLP-G07`, `TLP-G08` |
| The answer's identity is stable | `debt_tolerance` is a `Decimal`, never a float — the canonicalizer refuses floats as not bit-stable, and this value rides the content address | `TLP-G04` |

**Four of the 22 gates are marked `unavailable`, and that does not mean
"tested and passed".** Their failure state cannot be produced from this example
at all, because an SDK guard upstream prevents it. They are evidenced by the
working path plus that guard:

| gate | enforced upstream by |
| --- | --- |
| `TLP-G01`, `TLP-G02` | `D-IMPL-86` — the SDK refuses a divergent operator set at *bind* time, before a product exists |
| `TLP-G05` | the SDK's disclosure layer — it replaces a refusal's detail with its own sentence, so nothing written here can leak |
| `TLP-G08` | the SDK's type boundary — a refusal and a served product are different types |

We record this distinction because a reviewer is entitled to know which
guarantees this product holds and which the platform holds for it.

## Why you can trust these numbers

Every figure above came from a run against the live estate at commit
`db559c65`, asking `as_of=2026-06-17T18:05:00+00:00`. The default run serves
content address `6d29b32bbeef78e6…`. The content address is the check worth
running: it hashes the whole answer — the resolved entity, the entitlements,
the debt figure, the TTL window, the operator plan — so it only reproduces if
every input did. Re-run the command and compare.

**Illustrative calibration.** This example runs against a point-in-time
demonstration estate rather than continuously refreshed production data.
Freshness half-lives and related thresholds are calibrated to make the governed
behavior observable in that snapshot. They demonstrate how the SDK applies these
controls and should not be interpreted as recommended production coverage-policy
thresholds.

## What these runs do NOT show

- **No allocation advice.** The product reports the position the client holds.
  It proposes nothing, and `include_proposals` is declared and refuses.
- **No netting or set-off.** The deposit flags are carried through, not applied.
  That is a different product.
- **No FX exposure view.** Currency conversion happens so one total can be
  stated; the FX position question is a later rung.
- **No freshness claim about the client's own balances.** This estate records no
  observation time for them, and the product publishes that absence instead of
  filling it in. In a bank that timestamps its balances, this same product would
  age them — one line of configuration, no code.
- **Regulatory framing is general.** Where the posture is described as
  "enhanced scrutiny", that is this estate's synthetic overlay, not a citation
  to a named rule.
