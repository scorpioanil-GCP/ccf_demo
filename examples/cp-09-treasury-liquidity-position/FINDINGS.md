# cp-09 findings

The authoritative findings record for `treasury-liquidity-position`. Every
`CP09-F-NN` id resolves here. Status vocabulary is `D-IMPL-261`'s: **OPEN**,
**FIXED-`<phase>`**, **ESTATE-LIMITATION**, **NOT-A-GAP**. A constraint or an
estate property is not OPEN work.

---

## `CP09-F-01` — holdings carry no observation timestamp · ESTATE-LIMITATION

`deposit_account` and `investment_position` have no timestamp column at all.
The vault's §E declared *"deposit balances ~1 hour λ_c"*, which cannot be
computed against this estate.

**Not worked around.** The product adds a fourth temporal class,
`unobserved-holding`, publishes the absence, and never synthesizes an
`observed_at` from the request instant. Their envelopes carry
`observed_time=None` — a real field value, not a placeholder.

---

## `CP09-F-02` — the permitted-instrument KIND check is vacuous · ESTATE-LIMITATION

All 15 mandates permit all 3 instrument kinds, so no position is ever refused
on kind. The TENOR check is live: 34 of 200 positions exceed 365 days at
2026-06-17. Both run and are reported separately, so a reader can see which one
discriminated.

---

## `CP09-F-03` — `heldAt` and `concentratedIn` are one relation twice · NOT-A-GAP

Measured 2026-09-11: identical on all 200 positions, 0 divergence. The product
reads `concentratedIn` and records which; composing both would claim
information the estate does not carry.

---

## `CP09-F-04` — the vault's store assignment is correct · NOT-A-GAP

Confirmed against the estate. No reassignment needed.

---

## `CP09-F-05` — five time universes, no common live instant · ESTATE-LIMITATION

Ruled at Gate 1 (Q1 a): three pinned `as_of` scenarios rather than a single
invented "now" that would fail closed on everything.

---

## `CP09-F-06` — the SDK's reference freshness term cannot see a source's observation time · FIXED

**RESOLVED 2026-09-11 by `D-IMPL-331` and `D-IMPL-332`, recorded at
`D-GATE-cp-09`.** Dave took **option 2** below, and then a second ruling the
option list had not anticipated. Everything from here to *The decision for
Dave* is preserved as it was written when the finding was raised — the
measurement is the evidence, and rewriting it in the past tense would leave
nothing to check the ruling against.

**Why this entry read `OPEN` until 2026-09-12.** It was not re-stated when
the rulings landed, so cp-09's findings record and `docs/DECISIONS.md`
disagreed about whether an SDK issue was outstanding. That is not cosmetic:
the three-issue cap (CLAUDE.md §9) counts open SDK issues, and a stale `OPEN`
spends one of the three. Closed under `D-GATE-cp-10` (Dave, 2026-09-12).

---

**The finding as raised.** This is an SDK finding, and it disproves an
approved term of `CP-SPEC-009`. Raised, not resolved (CLAUDE.md §11).

**What the spec approved.** §E.1 declares a per-class λ_c table as *the decay
model*, and §E.2 says `F` is *"normalized over the participating
freshness-bearing classes … each participating class decays against its own
λ_c"*.

**What the build measures.** `F = 1.000000`, exactly, on a serve carrying three
observations **65,100 seconds old** against their own declared 86,400-second
half-life.

```
C (deployment-measured) = 0.5714      # limit coverage 4/7 × identity 7/7
S (deployment-measured) = 1.0000
D_c (SDK)               = 0.42860000
=> implied F            = 1.000000
```

If `F` measured source age, those three FX observations would each sit at
`2^(-65100/86400) ≈ 0.594` and `F` over the eight registered observations could
not be 1.

**The mechanism, read off the tree.**

- `src/ccf/assembly/worker.py::_stitch` — *"`observed_at` is always ingestion:
  it records when **the fabric** learned the claim"*. The source's
  `observed_time` becomes `valid_from`, a different field.
- `src/ccf/products/debt_scorer.py::_observations` builds
  `Observation(observed_at=record.claim.observed_at, …)`.

So `F` measures *how long ago the fabric learned a claim*, which in a per-run
fabric is zero for everything, and never *how old the source's observation is*.
The declared λ_c table is registered, is read, and cannot move the `F` term.

**Why it did not surface before.** `D-GATE-cp-08` recorded `D_c = 0` on every
answer under every scorer and attributed it to *"every observation is minted
from a live read inside the run"*. That reading is correct as far as it goes,
but it located the cause in the ESTATE. Measured here, the cause is in the
**mapping**: even an observation whose source time is 18 hours old ingests with
`observed_at = now`, so no estate — live, historical or perturbed — could move
`F` through this path.

**What this product does in the meantime, and what it does NOT do.** The real
ages are carried in the payload's `signal_register`, measured against the
decision instant, and the declared product gate refuses on them — so the
product's *refusal* behavior is correct and `TLP-G07` holds. What is not true
today is the spec's claim that λ_c drives `F`.

**Not worked around.** A deployment-supplied `debt_scorer` reading
`claim.valid_from` would make this example's number right and leave the SDK's
reference path wrong for everyone else, which is the shape `D-IMPL-289`
forbids: compensating code that reconstructs what should have been declared.

**The decision for Dave**, stated without a recommendation being taken:

1. the reference scorer reads `valid_from` when the source supplied one, and
   `observed_at` otherwise; or
2. `Observation` carries both and the half-life entry declares which axis it
   decays against; or
3. the spec is corrected to say `F` measures fabric-learning latency, and the
   per-class λ_c table is documented as governing supersession and TTL rather
   than `F`.

**Reproduce with:** the block above, from
`examples/cp-09-treasury-liquidity-position/run.py` against the curated estate
at `as_of=2026-06-17T18:05:00+00:00`.

---

### The resolution

**Option 2, and then the half nobody had listed.**

**`D-IMPL-331`** — a λ_c row declares WHICH of an observation's two instants it
decays against. `Observation` carries both; `HalfLifeEntry.decay_basis` selects;
a row declaring `valid-from` where no instant exists refuses by name with
`MissingDecayInstant` rather than falling back. The default is `observed-at` and
the field is hash-transparent, so every table written before it existed keeps its
identity and its `F`.

**`D-IMPL-332`** — and this is the part the three options above did not reach.
`_stitch` wrote `valid_from = envelope.observed_time or envelope.ingestion_timestamp`,
so a claim produced by the fabric **never** had a null `valid_from`. 331's
refusal guarded only the direct-construction path; through assembly, a
`valid-from` row read a manufactured instant and reported perfect freshness for
an observation whose real age nobody knew. Dave's ruling, verbatim: *"Unknown
must remain unknown. The CCF must never turn 'we learned it at 2 PM' into 'it
became true at 2 PM.'"* An unsupplied valid-time now stays **absent**, and every
validity-window read was taught to treat absence as *"in force"* rather than
*"out of range"* (`docs/GRAPH_QUERY_SEMANTICS.md` 1.4.0, `GQ-09`).

**Measured after the fix.** cp-09's `F` reads **0.970232**, against the
`1.000000` recorded above. The λ_c table is live on the freshness term.

**Why both halves were needed.** A declaration the layer beneath cannot honor is
decoration; an honest substrate nobody interrogates is unused. Dave's framing:
*"`D-IMPL-331` made the temporal basis explicit; `D-IMPL-332` ensured the
assembly layer no longer destroys the uncertainty required to enforce it."*

**Where it went next.** `CP10-F-07` found the remaining half of the same
question at rung 10 — 331 and 332 settle *which instant* and *whether there is
one*; `D-IMPL-333` settles *which observations constitute the thing being
scored*.

## Security remediation — `EX-09` (2026-10-07)

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before the change: §B.4, the example's own code rather than the SDK. Changed under `D-IMPL-261`'s "objectively wrong" reason, authorized by `D-IMPL-376` ruling (7): *"SDK input rejection is useful defense, but leaves fragile example code for adopters to copy."*

- **`EX-09`.** `acquisition.py::_Relational.rows` built `SET search_path TO {schema}` by f-string (security review 2026-09-23). It now composes the statement with the driver's own `psycopg.sql` — `SQL("SET search_path TO {}").format(Identifier(schema))` — so the configured schema reaches PostgreSQL as one quoted identifier, whatever it contains. The documented schema `ccf_v2` is one lowercase identifier, so it names the same schema quoted or not.

Evidence: `tests/examples/test_ex_09_search_path_identifier.py`.
