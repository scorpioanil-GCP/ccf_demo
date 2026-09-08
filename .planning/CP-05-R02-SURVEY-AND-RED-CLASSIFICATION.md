# R-02 payload survey, and the three remaining cp-05 reds classified

**Two bounded measurements requested by Dave, 2026-09-08.** No edits, no fixes, no new
tests, no scope beyond what each asks. Everything below is a read or a run; nothing in
`src/`, `runtime/`, `tests/` or any example was modified to obtain it.

---

## 1 · The R-02 payload survey — and the blocker it hit

**Asked for:** *"survey cp-00 through cp-04 payloads and report only: product →
non-canonical value shapes currently present → whether construction would newly refuse."*

**Method.** One subprocess per example, each with `ContextProductContract.__init__` wrapped
by a probe that runs `canonical_bytes(payload)` exactly as the proposed validator would,
then the example's own `run.py::main` invoked. Nothing is patched in the SDK; the probe
wraps and delegates.

| product | contracts built | non-canonical shapes | would construction newly refuse? |
| --- | --- | --- | --- |
| cp-00 institutional-holders | **0** | **not measurable** | unknown — see below |
| cp-01 counterparty-reference-snapshot | **0** | **not measurable** | unknown |
| cp-02 facility-terms-snapshot | **0** | **not measurable** | unknown |
| cp-03 obligor-financial-spread | **0** | **not measurable** | unknown |
| cp-04 corporate-family-tree | **0** | **not measurable** | unknown |
| cp-05 credit-exposure-rollup | 1 | **none** | **no — clean** |

### THE SURVEY COULD NOT BE COMPLETED, AND THE REASON IS LARGER THAN R-02

**None of cp-00 through cp-04 reaches contract construction against the current SDK.**
Two distinct pre-existing incompatibilities, both confirmed **on `main`** as well as on this
branch — neither is caused by anything in this session:

- **cp-01, cp-02, cp-03, cp-04** — `ProductRequestContract` refuses at construction:
  *"the request contract for 'reference.counterparty' at class lane '1.0.0' declares
  'intent' under arguments.properties, which is a shadow of the top-level request field
  ProductRequest.intent … remove the argument (`D-IMPL-264` D-01, amendment 1 F-2)."*
- **cp-00** — `TypeError: build_replay_record() missing 1 required keyword-only argument:
  'resolution'` at `produce.py:423`.

Both are the SDK moving out from under frozen specimens, which `D-IMPL-261` says is exactly
what a frozen specimen is for: *"a difference between two rungs is evidence about the SDK's
evolution."* They are recorded here as **measured, on `main`, today** — not repaired, not
quarantined, not counted as R-02's business.

**Consequence for R-02:** the blast-radius question Dave asked cannot be answered by
execution. Five of the six products cannot be run to the point where a payload exists.

### A static upper bound, labeled as such

Not a measurement of payload contents — an upper bound on where a float could enter. Two
`float(` call sites exist across all six examples:

| site | on a payload path? |
| --- | --- |
| `cp-01/deployment.py:281` — `float(_declaration(QUESTION)["debt_tolerance"])` | **No.** It feeds a tolerance, which R-02's proposed validator does not read |
| `cp-05/produce.py:388` | a **comment** recording the float that was removed, not a call |

So the tree's *visible* float exposure is one site, not on a payload path. That is weak
evidence and is offered as such: a float can reach a payload from a driver, a JSON parse or
an arithmetic promotion without any `float(` appearing in the example's own source, and
none of that is readable statically.

### What this leaves for Dave

The survey's stated precondition — *"If the blast radius is clean or clearly correct, then
R-02 can proceed"* — is **not established**, and cannot be established by this route. Three
options, none taken here:

1. **Proceed on cp-05's evidence alone.** One product, measured clean.
2. **Make the survey possible first**, which means the five specimens' pre-existing
   incompatibilities are dispositioned — a much larger question than R-02, and one
   `D-IMPL-261` bears on directly.
3. **Change the enforcement seam.** If the vessel cannot be surveyed, the shared
   canonicalization boundary may belong somewhere a survey *is* possible.

---

## 2 · The three remaining cp-05 reds — one issue with two faces

`tests/invariants/test_present_tense_sweep.py`, three failing assertions:

| assertion | what it reports |
| --- | --- |
| `test_no_superseded_phrase_survives[…/README.md::never clamped]` | lines 176, 271 |
| `test_no_superseded_phrase_survives[…/run.py::never clamped]` | line 328 |
| `test_the_declared_cp_04_debt_is_exactly_what_the_tree_carries` | those same three sites are absent from `CP04_KNOWN_DEBT` |

They are **one issue**: cp-05 introduced three new sites of a tree-wide superseded phrase
and is not on the declared-debt roster. The third assertion is the roster equality catching
exactly that drift, which is it working.

### Classification: NOT a product defect

**The phrase is accurate at all three cp-05 sites.** Measured against the live estate:
`--depth 6` is refused by the class's declared maximum of 5 (`D-IMPL-259`), `--depth 9` by
the technical maximum of 6 (`D-IMPL-253` Q21). **Neither is clamped; both are refused by
name.** cp-05's sentences say so and are true.

**The supersession's premise is cp-04-specific.** Its own reason states it:
*"the promise survives, but every sentence carrying it on this tree states it OF the
deleted bound of 6. Plan 24.6-13 restates it of the technical limit; until then each site
is declared debt below."* The ban is a temporary blanket taken while cp-04's sites were
stale, with a per-site debt roster beside it. cp-05 was authored after that roster was
pinned and states the phrase of bounds that exist.

So this is **roster bookkeeping**, not a false claim in the product and not an overfitted
invariant. Two dispositions, neither taken:

1. **Reword cp-05's three sites.** The phrase is banned tree-wide pending a restatement,
   and cp-05 can say the same thing in the SDK's own words — the real refusals say
   *"refused by name rather than silently narrowed."* Three lines.
2. **Add the three sites to `CP04_KNOWN_DEBT`.** Mechanically correct; the constant is
   named for cp-04 and would become a misnomer.

**Recommendation: (1).** It removes the debt instead of registering it, and it does not
require a cp-04-named constant to carry cp-05's rows.

### The fourth red is not cp-05's

`test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]` fails **on `main`**.
Pre-existing, out of scope, untouched.
