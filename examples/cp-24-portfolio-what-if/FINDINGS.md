# CP-24 — Portfolio What-If / Stress · FINDINGS

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B **before
remediation**. Every measurement was taken against the live estate on
**2026-09-21** with `CCF_REQUIRE_ESTATE=1`.

**Active SDK issue cap: 0 of 3.** No finding here is a new SDK gap. One is a
carried residual (`D-IMPL-304`), one is the ruled friction measurement, three
are defects in **my own proof machinery**, and the rest are estate or design
consequences. **No new SDK decision id was spent.**

---

## 1 · SDK capability proven (§K.1)

| Launch-contract item (§D) | How this rung exercised it |
|---|---|
| define contracts as Control Plane artifacts | the first **closed** object request parameter, one declared level |
| apply authorization and policy before use | the role decides which impacts are assembled |
| refuse correctly, by name, as data | `undeclared-parameter`, `type-mismatch`, `scenario-out-of-bounds`, `not-in-book`, `unpriced-intent` |
| preserve product identity and content addressing | the same canonical assumptions replay to the same address; a changed one does not |
| calculate Context Debt correctly | from **observed evidence only** — `WIF-G13` proves the scenario cannot move it |
| propagate lineage by declared semantics | observed claims carry `L`; assumptions carry none and live in the effective request |
| replay and reconstruct | **the first replay of a hypothetical** |

---

## 2 · SDK friction observed (§K.2)

### `WIF-F-01` — the population reader, written a second time
**Category 3, and the ruling made it a MEASUREMENT.** CP-24 is a sibling of
rung 23, so its book, member and facility readers are rung 23's, adapted.
Measured: of the ~1,300 lines in rung 23's three core modules, the population
half (`_members`, `_facilities`, the roster and ceiling reads, the canonical
member set) is **roughly 180 lines** carried across substantially unchanged.

**This is the second instance and nothing is abstracted.** Dave's ruling: if a
later rung produces a third substantially identical population reader, **all
three are measured before documentation or an SDK abstraction is considered.
No abstraction is pre-authorized.**

### `WIF-F-02` — the float refusal is a RAISE, not a governed envelope
**Category 3, CARRIED from `D-IMPL-304`.** A bare JSON fraction is refused —
loudly, by name, and **never coerced**, which is the half the ruling requires.
But the refusal happens inside `canonical_bytes` during request
canonicalization, **before the request contract is consulted**, so it arrives
as a `CanonicalizationError` rather than a governed refusal carrying a replay
reference. Measured at both a top-level `integer` parameter and a nested
scenario member: both raise.

By contrast, an **undeclared** member and a **type mismatch** *do* produce
proper governed refusals (`product-request-violation / undeclared-parameter`
and `/ type-mismatch`), because those checks run after canonicalization
succeeds. **Not repaired here, and no SDK change proposed:** the deployment
adds a typed check at its own seam so an adopter gets a diagnostic naming the
parameter and the canonical unit, and the SDK's refusal remains the backstop.

---

## 3 · Launch blockers (§K.3)

**None.** None of the five Gate-2 stop conditions fired. In particular the
fact-versus-hypothetical boundary was preserved throughout (condition 4), and
the duplicated population reader came in at the second-instance expectation
rather than materially larger (condition 5).

---

## 4 · Backlog candidates (§K.4)

Nothing new. `WIF-F-02` is carried under the existing `D-IMPL-304` residual and
`WIF-F-01` is a measurement awaiting a possible third instance.

---

## 5 · Estate / example limitations (§K.5)

### `WIF-F-06` — the book's oldest collateral observation is 545 days old
Measured across the demonstration book's 60 collateral assets: ages run **0 to
545 days**. That is honest evidence and is **not refreshed to make the stress
result cleaner**. Two consequences are carried rather than hidden: a stressed
stale valuation is reported as still stale (`WIF-G11`), and the book's
worst-member freshness decays to **0.1226** on the declared half-life, which
drives the debt tolerance below.

### `WIF-F-07` — the debt tolerance is calibrated to that staleness
`default_debt_tolerance` is **0.98**, an illustrative calibration under
`D-IMPL-323`. At rung 23's 0.95 every answer is withheld, because the
worst-member freshness above puts `D_c` at 0.941 before any scenario is
applied. Withholding every answer would make the scenario mechanism
unobservable rather than demonstrating it. **The staleness is not hidden by the
looser tolerance** — it drives the number, it is reported per observation, and
it is the subject of its own gate.

### `WIF-F-08` — 11 of 25 members have no facility, and 13 have no collateral
They remain members; no interest impact is computed for the first group and no
stressed collateral for the second, and both facts are named findings. Rung
23's rule, unchanged.

---

## 6 · Proof-machinery defects — mine, corrected, recorded

Three sabotages left their gate green and two did not match the source at all.
None was a product defect; all five were my own.

### `WIF-F-03` — `required` is not what makes an object closed
Emptying the scenario's `required` list left `WIF-G02` green, because the gate
asserts that an **undeclared** member is refused — which `properties` governs,
not `required`. Corrected to open the object itself.

### `WIF-F-04` — a sabotage that touched no real member
Injecting a random collateral age under a key no member carries left
`WIF-G13` green. Corrected to the sabotage the gate is actually about: making a
member's completeness depend on the scenario's rate shift, which is precisely
what the governing rule forbids.

### `WIF-F-05` — pinning one member of a two-member difference
Pinning only `rate_shift_bp` left `WIF-G16` green, because the two
demonstration scenarios differ on **two** magnitudes. Corrected to pin the
whole echo. The `ABS-F-09` shape a third time: **a sabotage must target the
claim the gate makes, not one field the claim mentions.**

### And two that did not match the source
The `WIF-G09` and `WIF-G17` sabotage strings were written against code that did
not exist at that indentation or at all. They failed loudly as `NO-MATCH`
rather than silently passing — which is the harness working — and were
rewritten against the real source.

---

## 7 · Product result (§K.6)

`BKR019` at `2026-08-25` under `{rate_shift_bp: 150, collateral_shift_bp:
-1000, collateral_class: real_property}`:

- **Observed:** SOFR **3.63 %** at 2026-08-20; 60 collateral observations aged
  0–545 days; 25 members, 14 with a drawn facility.
- **Derived:** the shifted rate **5.13 %**; incremental annual interest of
  **117,438,981.75** on the largest drawn balance; 28 real-property assets
  stressed −10 % with their ages intact; of 9 members with both drawn debt and
  collateral, **2 fall below the 10000 bp coverage floor**, named.
- **Debt:** `F=0.1226 C=0.4800 → D_c=0.9412`, from observed evidence alone —
  **identical** under the alternate scenario.

**What a consumer may rely on:** which figures are observed and which are
assumed; the assumption behind every derived value; that stressing did not
refresh anything; that the debt describes the evidence and not the scenario;
and that the same assumptions replay to the same address.

**What it may not rely on:** any forecast, probability or expected loss; a
refreshed valuation; or regulatory large-exposure arithmetic, which is CP-21's.
