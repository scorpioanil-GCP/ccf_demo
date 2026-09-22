# cp-21 — findings

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md`. **Nothing here was
repaired by changing the example to make it pass** (`D-IMPL-261`): where the
SDK or the estate fell short, the shortfall is recorded and the evidence stays
executable.

Measured 2026-09-21 against the live estate (`CCF_REQUIRE_ESTATE=1`).

---

## Summary

| id | class | disposition |
|---|---|---|
| `LEX-F-01` | estate limitation | recorded, served honestly |
| `LEX-F-02` | SDK gap, carried | `D-IMPL-304` residual, not repaired here |
| `LEX-F-03` | specification divergence | recorded with the structural reason |
| `LEX-F-04` | estate limitation | disclosed in the payload, never minted |
| `LEX-F-05` | proof machinery (mine) | fixed |
| `LEX-F-06` | proof machinery (mine) | fixed |
| `LEX-F-07` | example defect (mine) | fixed — a No-Hardcoding violation |
| `LEX-F-08` | estate limitation | disclosed in the payload |
| `LEX-F-09` | friction measurement | **not** a third instance; nothing requested |

**Issue cap (CLAUDE.md §9): one SDK issue is open from this rung** —
`LEX-F-02`, which is a known carried residual rather than a new one. `LEX-F-03`
is a specification/design divergence, not an SDK defect.

---

## `LEX-F-01` — a connected group extends beyond the LEI-registered set

**Estate limitation. Recorded, and the members are served rather than dropped.**

Measured: the estate carries **188 connection edges** (184 control, 4 economic
dependency) spanning **167 nodes**, of which **106 resolve to a `legal_entity`
row and 61 do not**. Those 61 are real group members that carry no LEI, and
therefore no measurable exposure.

Dropping them would shrink the group and understate the denominator of every
ratio — which is precisely the *Context Starved* failure this product exists to
refuse. So they are emitted with `lei_registered: false`, they count toward
`member_count`, and the payload carries a standing finding saying so.

**Not an SDK gap.** The SDK served exactly what it was given.

---

## `LEX-F-02` — the noncanonical-magnitude refusal is raised before the contract boundary

**SDK gap, carried unchanged from rung 24. Not repaired here.**

`canonical_bytes` refuses a `float` as not bit-stable, which is correct and is
the real backstop. But it refuses by **raising during request
canonicalization**, before the request contract is consulted — so the refusal
is loud and nothing is coerced, yet it is not a governed refusal carrying a
replay reference. That is the `D-IMPL-304` residual shape.

`produce.large_exposure_question` adds a diagnostic an adopter can act on —
naming the parameter and its canonical unit — and **does not** repair the SDK
behavior. `LEX-G17` asserts the refusal, not the envelope.

---

## `LEX-F-03` — the specification's fourth operator is not buildable as specified

**Specification divergence, recorded with its structural reason. Not an SDK
defect.**

`CP-SPEC-021` §D.2 assigns step 4 — *retrieve the regime provisions supporting
each limit* — to the **Similarity** category, and §D.2 therefore implies four
declared operator keys. This deployment declares **three**.

The reason is structural, not a shortcut. `similarity.corpus-select` **ranks
entities that are already in the view** against a query, using an injected
index. It cannot retrieve anything from MongoDB: by the time any operator runs,
acquisition is over and the graph exists. The rulebook passages are therefore
resolved at the **acquisition seam**, where source retrieval belongs, and
travel as claims on the regime entity carrying their quoted text.

Declaring a fourth key anyway would have added an operator ranking three regime
nodes against a query nobody asked — scaffolding, not mechanism, and a vacuous
entry in the served plan. `LEX-G01` asserts the served plan against **this
class's declaration** rather than a fixed four, which is what makes the
divergence visible instead of hidden.

**What it suggests for the backlog:** the step table in the Context Product
Specification Standard conflates *"which category does this work belong to
conceptually"* with *"which operator key runs in the plan"*. Those are
different questions whenever the work is source retrieval rather than view
narrowing.

---

## `LEX-F-04` — this estate exposes no ledger point

**Estate limitation. Disclosed in the payload; never minted.**

Measured: the Fluree deployment at `.76` emits **no `x-fdb-t` header** on its
SPARQL endpoint, and no route returning the ledger `t` responds — `/fluree/query`
and `/fluree/ledgers` are 404, and a commit-metadata query returns empty. So
the point at which the group was derived is **not recoverable from this
estate**.

The payload therefore reports `ledger_t: "unreported"` alongside
`ledger_point_resolvable: "false"`, and `LEX-G21` gates on that **disclosure**
— refusing a plausible `t` served beside a declaration that none resolved.
Gating on a value that is always `unreported` here would have been a vacuous
gate.

**This is not confined to cp-21.** `examples/cp-16-abs-securitization-surveillance`
and `examples/cp-24-portfolio-what-if` read the same header through the same
route and will have been recording `"unreported"` silently. Worth a sweep when
those rungs are next touched — **not** repaired here, since they are frozen
specimens.

---

## `LEX-F-05` — a gate limb that could not fire

**Proof-machinery defect. Mine. Fixed.**

`LEX-G14`'s fused-freshness limb scanned the payload's **top-level** keys for
`combined_freshness_at` and friends. But the declared-shape check earlier in
the same gate refuses **any** undeclared top-level key, so the sabotage
reddened a different limb and this one was dead code — it could not fire under
any input.

Found by running the positive control, which is what positive controls are for.
The scan is now recursive, and the sabotage mints the key **nested inside
`freshness_asymmetry`** — which is both the reachable place and the likelier
real-world shape, since a product fusing two clocks would put the fused value
where the clocks are.

Three further `LEX-G14` controls were added at the same time: an asymmetry
declared `resolved: true`, a capital base that lost its own date, and a ratio
carrying a capital date other than the base's.

---

## `LEX-F-06` — a test that passed for the wrong reason

**Proof-machinery defect. Mine. Fixed.**

`LEX-G05`'s positive control asked its "earlier instant" question at
**2021-06-01**, chosen because the estate's CRR regime is in force there. But
the `bank_capital` series **starts 2023-06-30**, so at any 2021 instant the
product refuses with `no-capital-base` — for a reason that has nothing to do
with regime selection.

Measured: with the `effectiveFrom` check disabled, the test **still passed**.
It was asserting a refusal the sabotage could not remove.

The two windows — CRR in force, and capital observable — **do not overlap in
this estate**, so that particular pair is unprovable here and is recorded as
such. The control instant moved to **2025-06-01**, where capital exists and
Regulation O is not yet in force, and a companion assertion now proves the
**same instant serves** under `pra-2022`. With that, disabling `effectiveFrom`
turns the test red.

**The transferable shape:** a test asserting a refusal must show that the
refusal it got is the refusal it meant. Asserting *"something refused"* is not
asserting *"this rule refused"*.

---

## `LEX-F-07` — a routing vocabulary hard-coded in example code

**Example defect. Mine. Fixed. It was a No-Hardcoding Rule violation.**

`acquisition.connection_bases()` returned a literal tuple
`("control", "economic-dependency", "both")`. `connection_basis` **decides the
answer** (`LEX-G04`), so its admissible set is a routing vocabulary, and
CLAUDE.md §6.4 puts routing vocabularies in artifacts, not code.

The consequence was not cosmetic: widening the declared domain in
`ccf_config.yaml` changed nothing, because the acquisition seam consulted its
own copy — so `LEX-G03`'s sabotage **could not redden the gate**. The gate was
green because of a second, undeclared guard.

The vocabulary moved into `artifacts/source-vocabulary.yaml`, and `LEX-G03` now
also asserts that the acquisition seam and the request contract's
`argument_domains` **agree** — so a domain widened in one place and honored in
the other is caught rather than silently admitted.

---

## `LEX-F-08` — guarantee-based mitigation is not measurable in this estate

**Estate limitation. Disclosed in the payload rather than papered over.**

`guarantee_terms` holds 28 rows. Measured: **4** name an obligor that resolves
to a facility-holding entity; the rest say so in their own `note` field —
*"parent guarantees a subsidiary that holds no facility"*. Resolved per group:
Bausch gives 2 and receives 2, Super Micro gives 4 and receives 1, TransDigm
neither gives nor receives any.

**But the recognized cover is zero in every case**, because every covered
obligor holds no facility — a guarantee over an obligor with no exposure
relieves nothing, however generous its percentage. The product computes that
from the exposure it already acquired rather than asserting it, and serves a
finding saying so.

So the eligible mitigation this estate can actually recognize is **undrawn
commitment relief**, and that is what `apply_mitigation` controls here. The
payload does not present a single netted figure: it names which component
applied (`undrawn-relief-recognized`,
`undrawn-excluded-by-counting-rule`, `guarantees-given-counted`) and reports
both mitigation components available.

**A bug of mine was found measuring this.** `guarantees_received` compared
`_slug(_local(obligor_uri))` against `_slug(legal_name)` — but `_local` of a
graph URI is *already* slug-shaped, so the second `_slug` lower-cased the
interior capitals and the join matched **nothing**, silently. The count read
zero everywhere and looked like a clean estate fact. It was found only by
re-measuring a figure before shipping it in this document.

This is what makes `LEX-G15` non-vacuous on real data — and it reproduces the
estate's own `fits_after_mitigation` label exactly, with **$60.5 million** of
margin on a $73.940bn limit.

---

## `LEX-F-09` — the population reader: NOT a third instance

**Friction measurement, per the `Q2` ruling of rung 24. Nothing is requested
and nothing is pre-authorized.**

Rung 24 was ruled a **sibling** of rung 23, and the duplicated population-reader
plumbing was to be recorded as a friction measurement **at the second instance
only**. The question this rung owes is whether it is the third.

**Measured: it is not.**

| tree | reader | lines | shape |
|---|---|---|---|
| cp-23 | `_members` | 22 | reads a stored roster from `coverage_assignment` |
| cp-24 | `_members` | 22 | **byte-identical to cp-23's** apart from one spec citation |
| cp-21 | `_group` | 95 | derives a transitive closure from graph edges under a caller-selected basis |

cp-23 and cp-24 differ by a single comment line. cp-21's is a different
function doing a different thing: edge admission by basis, closure over a
component, resolution of names back to LEIs, and honest emission of members
that carry no LEI at all. It shares no code with the other two and could not.

cp-21 also has **no** `canonical_members` and no `member_digest` seam, because
its population is derived rather than supplied — there is nothing for a caller
to canonicalize.

**So the second-instance expectation stands unchanged, and this rung adds
nothing to it.** No abstraction is requested.

---

## What held without friction

Worth recording, because a findings file that only lists problems misreports
the build.

- **The paved producer road (`D-IMPL-343`)** took this product unchanged:
  `open_product` with a named `plan_factory`, `--8<--` boot and answer regions,
  and no SDK edit of any kind.
- **The standard door (`open_door`)** took its three typed overrides unchanged,
  and the closed `proposal` object crossed it **byte-identically** — the
  in-process and through-the-door determinations hash the same.
- **`compose_debt_factors` (`D-IMPL-104`)** composed member factors correctly
  with no reinterpretation, and a proposal provably cannot move the result.
- **`argument_domains` with `members`** refused an undeclared basis without
  narrowing it (`D-IMPL-251`), and the caller-facing `enum` was derived rather
  than authored (`D-IMPL-259`).
- **`D-IMPL-332`'s two observation types** carried the whole freshness
  asymmetry: standing state for membership, exposures and limits; dated
  artifacts for the capital base and the regime. That split is what made
  `LEX-G14` expressible at all.
- **No new `D-IMPL` was needed**, and no SDK source file was touched.
