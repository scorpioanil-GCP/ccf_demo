# CP-23 — Portfolio Early-Warning / Concentration · FINDINGS

**Accepted at `D-GATE-cp-23`, 2026-09-21**, on the candidate `cp-23-portfolio @ 2fcc2e87`,
merged `--no-ff` into `main`. **Paved-road implementation; no `src/` or `runtime/`
SDK behavior change.** 19 declared / 19 executing gates; all 19 observed red under
sabotage; none `unavailable`; 30 tests passed, 0 failed, 0 skipped; active issue
cap 0 of 3. **A coverage probe, not a Portfolio Management application.**

**Gate-id note:** the CP-21 boundary gate is `PEW-G18` in the shipped numbering
(it was `PEW-G17` at Gate 1, before `Q2` split the identity invariant and shifted
the ids); `PEW-G17` is now the covenant-history gate. Both are load-bearing.

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B **before
remediation**. Every measurement was taken against the live estate on
**2026-09-21** with `CCF_REQUIRE_ESTATE=1`.

**Active SDK issue cap: 0 of 3.** No finding here is a new SDK gap. One is a
naming friction the ruling explicitly declined to repair; one is a Gate-0
prediction corrected; four are defects in **my own proof machinery**; one is a
defect in **the product**, found by its own gate and fixed; the rest are estate
or design consequences.

---

## 1 · SDK capability proven (§K.1)

| Launch-contract item (§D) | How this rung exercised it |
|---|---|
| assemble from governed source reads | 25 members, four limbs, batched per limb rather than looped per member |
| apply authorization and policy before use | the role's member narrowing is formative at the acquisition seam |
| calculate Context Debt correctly | the SDK's `compose_debt_factors` over members, per-factor minimum |
| preserve product identity and content addressing | `PEW-G05`/`PEW-G06`: order-invariant, membership-sensitive |
| refuse correctly, by name, as data | `not-in-book`, `severity-floor-lowered`, `role-not-declared`, `unpriced-intent`, and a governed `tolerance-exceeded` withholding |
| replay and reconstruct | `PEW-G19`, including the canonical member set in the effective request |

---

## 2 · SDK friction observed (§K.2)

### `PEW-F-08` — `compose_debt_factors` names its sequence `children`

**Ruled at `D-GATE-cp-23`: a DX/naming observation ONLY — no combinator rename,
no widening to `Member`, no new SDK phase.**
**Category 3 (backlog note). Ruled not to repair.** The combinator implements
exactly the rule a population needs — per-factor minimum strength, explicitly
not `max(child D_c)` — but its parameter and docstring speak of *admitted
children of a composite*, and CP-23 has no children. Dave ruled (2026-09-21)
**use it anyway**, do not copy it, do not widen the SDK vocabulary to `Member`,
and do not open a naming phase. Recorded so the naming is a known cost rather
than a silent one; a later widening of the docstring would close it.

### `PEW-F-09` — Gate 0 predicted a low road this rung does not need

**Recorded at `D-GATE-cp-23`: CP-23 proved to be a paved-road rung and the
low-road guard is NOT added from it.**
**Category 3, a CORRECTION rather than a defect.**
`docs/GATE-0-COVERAGE-CP15-24.md` §4.1 names CP-23 *"the first low-road rung"*,
measured against cp-05's 2,382 lines over five files, and says it would measure
**A10** (`run_gates(touched_entities=None)` passing silently). Read against the
tree: `src/ccf/projection/engine.py::ExecutionResult.touched_entities` returns
every entity URI in the composed view, and `src/ccf/products/resolver.py`
threads it into the gate sequence on the governed path, so on the paved road
the argument is never `None`. **CP-23 is a paved-road rung and A10 does not
arise from it.** The `Q12(b)` guard was explicitly NOT added. A10 remains open
for a genuinely hand-built low-road caller.

---

## 3 · Launch blockers (§K.3)

**None.** No finding on this rung is category 1 or a ruled category 2. None of
the five Gate-2 stop conditions fired — in particular **stop condition 5 does
not fire**: `compose_debt_factors` was exercised directly before any product
code was written and behaves exactly as its ruled semantics require.

---

## 4 · Backlog candidates (§K.4)

### `PEW-F-02` — a severity floor is a real cost, and the product says so
**Category 4, and it is the SDK working.** Raising `severity_floor` to 0.9
narrows what the book looks at, thins each member's evidence, raises the
population's debt above the declared tolerance, and the product is **withheld**
with `tolerance-exceeded` rather than served thin. Recorded because a reader
will meet it, and because a governed refusal is a successful demonstration
(§A). No change proposed.

---

## 5 · Estate / example limitations (§K.5)

### `PEW-F-01` — this book cannot show that the ruled debt law differs

**Recorded at `D-GATE-cp-23`: the live book does NOT demonstrate a numerical
divergence and no such claim is made. Both figures stay visible and the positive
control is kept.**
The ruled law (per-factor minimum) and the forbidden one (`max(member D_c)`)
give **the same number on `BKR019`** — 0.88 — because the member weakest on
freshness also sits at the completeness floor. **The estate alone therefore
cannot discriminate the two laws**, and a test that only compared them on this
book would prove nothing. A positive control with three members each weak on a
*different* factor shows the difference: composed `D_c` 0.88 against
`max(member D_c)` 0.60. The product serves both numbers side by side and says
plainly when they coincide.

### `PEW-F-10` — the estate's covenant evidence is two cured breaches
Both of the estate's covenant breaches fall in this book, and both are cured
(`compliant_today = true`). **Active covenant pressure is genuinely zero.** The
member states zero active and two historical rather than being omitted — rung
15's *a finding is not an absence*, a third time.

### `PEW-F-11` — 11 of 25 members carry no facility
They remain members and their signals count; the facility-covered count is
stated. Dropping them would make the book's utilization read as the whole
book's.

### `PEW-F-12` — the book is a current roster, not a bitemporal one
`coverage_assignment` carries an `assigned_date` and no end date, so
membership is a **standing state** (`supersede-only`) and this product does not
claim to reconstruct a historical book.

---

## 6 · Proof-machinery defects — mine, corrected, recorded

Four sabotages left their gate green, and one gate found a defect in the
product rather than in a sabotage.

### `PEW-F-03` — one `PEW-G09` limb is unreachable behind a stricter gate
Adding a book-wide `portfolio_freshness_at` key is refused — but by the SHAPE
check (`PEW-G07`), because any added key changes the payload's member set. The
freshness limb that names the key is therefore **defence in depth** and can
only fire if the declared member set were ever widened. Stated in the test
rather than hidden; the reachable `PEW-G09` sabotage is the empty-rows one.

### `PEW-F-04` — the containment gate could not tell which mechanism refused
Removing the roster check left `PEW-G04` green: a bogus member simply produced
no claim, the population came out short, and `PEW-G03`'s count check refused
instead. The gate now asserts the refusal **at its own seam** so the mechanism
under test is the one observed.

### `PEW-F-05` — the product address could not prove canonicalization

**Ruled at `D-GATE-cp-23`: payload sorting is NOT evidence of request
canonicalization; the load-bearing proof reads the effective request from replay
evidence.**
The payload sorts its own population, so two orderings give the same content
address **whether or not the request was canonicalized**. Removing the sort
left `PEW-G05` green. The gate now reads the canonical `members` out of the
effective request in the replay record, which is where canonicalization
actually has to land.

### `PEW-F-07` — a single-field pin cannot collapse two books
Pinning `banker_id` in the payload left `PEW-G19` green, because two books
differ on many axes anyway. The sabotage that works makes acquisition ignore
the subject entirely. The `ABS-F-09` shape, a second time: **a sabotage must
target the claim the gate makes, not a field the claim mentions.**

### `PEW-F-06` — the entitlement looked FREE, and the gate caught it

**Corrected denominator recorded at `D-GATE-cp-23`: after caller-request
narrowing, before role-based entitlement exclusion. Caller narrowing must not
reduce completeness; role exclusion must remain visible. The gate that caught it
is preserved.**
`PEW-G13` found a defect in the **product**, not in a sabotage. The `product`
role, which sees only facility-covered members, originally reached completeness
**1.0** and a *lower* `D_c` (0.861) than the `coverage` role's (0.943) — so
excluding members made the book look more complete. Corrected: the book now
carries its full in-scope roster and completeness is scaled by the share the
role was served. A second correction followed immediately: the first fix also
penalized a caller who *narrowed its own question*, which denies it nothing —
so the denominator is now the scope **after the caller's narrowing and before
the role's**.

---

## 7 · Product result (§K.6)

`BKR019` at `2026-08-25`, as the coverage role: 25 members, 14 with facilities,
utilization 34–67 %; **868 signals** tiered 89 action-red / 426 warning-amber /
353 informational-blue; five signal classes with ages 53, 52, 51, 14 and 12
days, weakest first; population debt by per-factor minimum `F=0.40 C=0.50
S=1.00`, naming the member behind each weak factor. To the credit role,
additionally: zero active covenant breaches against two historical and cured,
and a single-name concentration of **60.64 %** against this rung's declared
25 % threshold.

**What a consumer may rely on:** the population it was served and how large the
book actually is; which signal class is weakest and by how much; which member
each weak debt factor came from; that two orderings of one membership are one
determination; and that no regulatory large-exposure arithmetic was involved.

**What it may not rely on:** a historical reconstruction of the book; active
covenant pressure (there is none); forecasting of any kind; or the ruled debt
law differing from `max(member D_c)` *on this particular book*.

## Security remediation — `EX-09` (2026-10-07)

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before the change: §B.4, the example's own code rather than the SDK. Changed under `D-IMPL-261`'s "objectively wrong" reason, authorized by `D-IMPL-376` ruling (7): *"SDK input rejection is useful defense, but leaves fragile example code for adopters to copy."*

- **`EX-09`.** `acquisition.py::_Relational.rows` built `SET search_path TO {schema}` by f-string (security review 2026-09-23). It now composes the statement with the driver's own `psycopg.sql` — `SQL("SET search_path TO {}").format(Identifier(schema))` — so the configured schema reaches PostgreSQL as one quoted identifier, whatever it contains. The documented schema `ccf_v2` is one lowercase identifier, so it names the same schema quoted or not.

Evidence: `tests/examples/test_ex_09_search_path_identifier.py`.
