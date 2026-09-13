# D-IMPL-336 — cross-AI code review panel

**Subject:** branch `d-impl-336-composite`, tip `2b2770da`, base `main` `374a3600`
**Reviewed:** `src/ccf/products/composite.py` (755 lines), `src/ccf/peering/eligibility.py` (231), and the diff to `skills/catalog.py`, `products/contract.py`, `halflife/debt.py`, `replay/record.py`, `products/gates.py`, `products/refusal.py`, `products/disclosure.py`
**Date:** 2026-09-13 · **Status: NOT merged. CP-14 acquisition still HOLD.**

> **For the independent agents reading this.** Every finding carries the command
> that produced it. Nothing is asserted on a reviewer's say-so: five reviewers
> raised 32 claims, and **four that multiple reviewers agreed on were killed by
> one measurement each** — those are listed as rejected, with the measurement.
> Severities below are the *verified* ones, which are mostly lower than the
> reviewers proposed. Re-run anything.

---

## 1 · How the panel was run

The payload was **inlined source**, not file paths: on this host codex's sandbox
can exit 0 having read nothing, and a review of nothing is indistinguishable
from a clean review. It was fed on **stdin**, not argv, because a single argv
string caps at 128 KB and a larger one dies `rc=126` with zero bytes — which
also reads like a clean empty review. Payload: **76,942 bytes / 1,765 lines**.

Four already-known limitations were briefed to every reviewer *as known*, with
instructions to spend budget on what is **adjacent** to them.

| Reviewer | Invocation | Raised |
| --- | --- | ---: |
| **codex** (gpt-5.5) | `printenv CODEX_API_KEY \| codex login --with-api-key`, then `codex exec - < payload` | 5 |
| **codex, re-run** | first pass ran at `reasoning effort: none`; re-run with `-c model_reasoning_effort="high"` | 5 |
| **cursor** | `cursor agent -p --mode ask < payload` | 6 |
| **gemini** | `gemini -p "$(cat payload)"` | 5 |
| **ollama** | `ollama run gpt-oss:120b-cloud < payload` | 5 |
| **fable** | workflow agent, `model: fable`, `effort: high`, deliberately **not** shown the others' findings | **11** |

Then **13 adversarial verifiers**, one per distinct claim, each required to
execute code against the tree and prompted to *refute by default*. Their
verdicts corrected several findings and downgraded most severities.

**Fable was the strongest reviewer by a distance** — it found four defects
nobody else did, including the most consequential one, and it was the only
reviewer to read the tests and find a defect in them.

---

## 2 · The finding that reframes all the others

### F0 · The composite surface has no callers · **CRITICAL**
*fable alone; independently rediscovered by the verifier assigned to refute F10.*

```
$ grep -rn "resolve_producing_grant\|CompositeAdmissionGate\|compose_children\|AdmittedChild" \
      src runtime --include=*.py | grep -v "^src/ccf/products/composite.py"
  (no output)

$ grep -rn "child_resolutions" src runtime --include=*.py
  src/ccf/replay/record.py:1159      # the field declaration; nothing writes it

$ grep -rn "\.requires\b" src runtime --include=*.py
  src/ccf/products/contract.py:970   # its own registration validator
  src/ccf/products/composite.py:617  # a docstring cross-reference
```

And the reach test the F10 verifier ran, which is worse:

```
register_product_class accepts 'requires':          False
ProductClassDeclaration has field 'requires':       False
ProductClassDeclaration extra policy:               forbid
declaration refused a 'requires' kwarg:             ValidationError
```

**A governance author has no supported path to declare `requires` at all**, and
even by direct construction nothing reads it. A product class that somehow
carried requirements would be served by `run_gates` with no composition, no
admission, and no replay rows. `child_resolutions` is a field nothing writes.

This is `D-IMPL-324` — *declaration is not a door* — applied to the entire
feature, and the module docstring cites that very ruling.

**It is also why every finding below is scored lower than it looks.** Nothing
external reaches this code today, so none of the gaps are currently exploitable
by an untrusted principal. That is the one piece of good news, and also the
reason the gaps went unnoticed.

---

## 3 · CONFIRMED findings

All are reachable by the **in-boundary composite assembler** — the caller these
mechanisms exist to constrain — and none by an untrusted principal today.

### F1 · A governance rejection of an optional child costs nothing · **MED**
*codex, gemini, cursor, fable — 4 of 5 independently.*

```
optional requirement, completeness_when_absent = 0.6
  A declared-absent          status=optional-absent        C=0.6  D_c=0.4
  B REFUSED (ineligible)     status=ineligible             C=1    D_c=0
  B2 REFUSED (as-of)         status=rejected-at-admission  C=1    D_c=0
  C ADMITTED healthy         status=admitted               C=1    D_c=0
  D ADMITTED degraded        status=admitted               C=0.6  D_c=0.4   <- positive control
```

For an optional requirement the `ChildAdmissionRefusal` branch appends a row and
`continue`s, contributing **no debt factors**. An *ineligible* child is
arithmetically indistinguishable from a flawless one. Row D proves the harness
can see a contribution when one exists.

**The obvious fix is foreclosed.** `OptionalAbsenceTreatment`'s own docstring
rules that *"absence is not refusal, invalidation, or unauthorized access, and
this contract governs only the first."* So reusing `completeness_when_absent`
for a refusal is forbidden by D-IMPL-336, and the SDK may not invent a value
(D-IMPL-38). **Closing this needs a newly declared cost or a ruling, not a
patch.** Replay is honest — the row records `ineligible` — so the defect is
confined to the served debt arithmetic.

### F2 · `AdmittedChild` is not re-bound to the requirement it satisfies · **MED**
*codex (both efforts), cursor, fable.*

```
class-A child filed under key "ClassB" for a required ClassB slot:
  gate's own verdict for that pairing: ChildAdmissionRefusal class-mismatch
  compose_children:  served=True   status='admitted'

1.0.0 child against a slot declaring compatible_from="1.2.0":
  gate's own verdict: ChildAdmissionRefusal version-incompatible
  tight.accepts("1.0.0"): False
  compose_children:  served=True
```

The gate refuses both pairings directly; `compose_children` composes them
anyway, because it keys on `outcomes.get(requirement.product_class)` and never
compares against `outcome.candidate.requirement` — a field sitting right on the
admitted object.

**Correction to the finding as raised:** the replay row is *not* wholly
mendacious. It carries the slot's `required_product_class` **and** the child's
true `child_schema_name` / `child_schema_version`, so an auditor comparing the
row against the class declaration can see the mismatch. What is absent is any
refusal.

### F3 · Omitting `touched_entities` skips eligibility **and falsely claims the register ran** · **MED**
*cursor, codex-high, fable.*

```
entity superseded at 12:15, child snapshot 12:00:
  touched_entities=('entity://obligor-alpha',) -> ChildAdmissionRefusal  ineligible
  touched_entities omitted                     -> AdmittedChild          basis='local-register'
  compose_children served=True; replay row: status=admitted basis=local-register
peered variant:
  touched omitted -> AdmittedChild  basis='producer-attested'
```

`ChildCandidate.touched_entities` defaults to `None`, and
`refuse_dependency_invalidation` treats `None` as a pass — a documented
pre-D-IMPL-334 compatibility posture, legitimate at the `run_gates` layer and
tested there. At the composite gate the consequence differs: `run_gates`
returning *served* claims nothing about a register, whereas `admit` returning
`local-register` is **a positive claim about an authority that was never
consulted**, and it is persisted into the replay row.

It also silently disables the local register's *refusal* limb for a **peered**
child, contradicting the source comment three lines above it: *"The local
register can always REFUSE."* The "always" is conditional on a defaulted field.

No test anywhere passes `None` at the composite gate; the test helper defaults
`touched=(ENTITY_OBLIGOR,)`, so all ~40 tests supply it.

### F4 · There is no authorization check at all · **MED**
*fable; cursor found the symptom.*

`candidate.skill_name`, `skill_version` and `grant_hash` are **caller-supplied**,
written verbatim into `ChildResolution`, and never compared with the entry
`resolve_producing_grant` returned. `admit()` never receives `bound_skills`. A
child produced by a skill the agent was never granted is admitted whenever
class/version/as_of/address/debt/eligibility pass, and replay records whatever
`grant_hash` the caller typed.

No SDK path therefore originates an `unauthorized` refusal — **the gate makes no
authorization decision at all.** (That is arguably by design: authorization is
decided at the child product's own delivery boundary. See F11 for what the
verifier established about the token itself.)

### F5 · `_tenant_id` is stored and never read — and the child picks its own register · **MED**
*codex, cursor; fable and the verifier found the sharper harm.*

```
AST census of CompositeAdmissionGate:  self._tenant_id  stores=[1]  loads=[0]

gate.tenant=alpha  child.tenant_id='tenant-alpha'  -> REFUSED[ineligible]
gate.tenant=alpha  child.tenant_id='tenant-bravo'  -> ADMITTED basis=local-register
  (identical bytes; only the label changed)
same inversion on the peered branch -> ADMITTED basis=producer-attested
```

`refuse_dependency_invalidation` resolves the register by the **child's
self-declared** `tenant_id`. That keying is deliberate and documented. The defect
is that nothing checks the child *is* this tenant's before trusting it — so
relabelling the tenant makes the child escape tenant A's supersession register
entirely, and the local branch then records `eligibility_basis='local-register'`
for a tenant that **has no register in this fabric**. A positively false audit
claim. `EligibilityAssertion` binds five facts and tenant is not among them, so
the peered path cannot repair it either.

### F6 · `ProducedHere` is unverified, and the mislabel is unauditable · **MED**
*codex; fable and the verifier sharpened it.*

```
one child, one gate, same bytes — only the LABEL changes:
  ProducedElsewhere('fabric://peer', header={})      -> REFUSED  eligibility-evidence-missing
  ProducedHere('fabric://peer')                      -> ADMITTED basis='local-register'
  ProducedHere('fabric://an-attacker-i-made-up')     -> ADMITTED basis='local-register'
  ProducedHere('')                                   -> ADMITTED basis='local-register'

fabric_id across all of src/ccf: 3 sites — its declaration, and two on the
ProducedElsewhere path only. On the ProducedHere branch it is write-only.
gate.__dict__ = ['_tenant_id', '_consumer_scope', '_registry']  — no local fabric identity exists to compare against.
ChildResolution fields: 17, and none of them names the producing fabric.
```

So the defect is not that the label is *unverified* — it is **unverifiable**,
both at admission (nothing to compare to) and afterwards (the replay row never
records which fabric the `local-register` claim was made about).

**One correction:** the local register is still consulted on the `ProducedHere`
path and can still refuse. What the mislabel skips is the *positive
establishment* of eligibility, not every check.

### F7 · `checked_at` is documented as load-bearing and enforces nothing · **MED**
*codex, gemini, cursor, fable — 4 of 5.*

```
checked_at honest (2026-03-01)      -> AdmittedChild producer-attested
checked_at 1970-01-01 (56y stale)   -> AdmittedChild producer-attested
checked_at 2999-12-31 (973y future) -> AdmittedChild producer-attested
checked_at before the graph snapshot-> AdmittedChild producer-attested

positive control — the other five bindings all refuse when lifted:
  address / as_of / producer / consumer_scope / invocation -> eligibility-evidence-mismatch
```

The module docstring says the assertion *"is bound to six facts, and admission
checks every one"* and lists six; `_binding_mismatch`'s own docstring says
*"All five bindings are checked."* **Five is the true number.**

**What the gap actually costs, stated precisely:** a *malicious* producer gains
nothing — `eligible` is itself producer-attested and unverifiable, so it would
simply assert `True` with a plausible timestamp. What is lost is the ability to
catch an **honest-but-stale cached** eligibility determination, or a skewed
producer clock. And `checked_at` never reaches `ChildResolution`, so it cannot
be audited afterwards either. Every other binding has a sabotage test; this one
has none — `checked_at` appears exactly once in the whole test tree, as the
honest default.

### F8 · The "single-use" replay defence does not exist · **MED**
*fable alone.*

```
$ grep -rn composition_invocation src --include=*.py | grep -v "composite.py\|eligibility.py"
  (no output)
```

No spent-set, no registry, no token consumption. `admit` called twice with the
identical candidate and identical `composition_invocation` returns
`AdmittedChild` both times. The docstring states single-use as a property the
gate *provides*. The tree already knows how to spend a token once
(`src/ccf/graph/_writer.py`), which makes the omission plainer.

### F9 · An address-mismatch refusal retains the forged address as evidence · **MED**
*codex at high effort only.*

The `refuse` closure captures `address = candidate.content_address` — the
reported, untrusted value. On `address-mismatch` the gate has just *proved* that
value wrong and computed the true one, yet records the wrong one as
`child_content_address`. Amendment 2 requires a rejected product's identity to
be retained as evidence; the retained evidence is the attacker-supplied string.

### F10 · `ChildRequirement.accepts` raises on a pre-release floor · **MED**
*fable alone.*

`accepts` does `int(part)` over `split(".")`; `"1.0.0-rc1"` becomes `"0-rc1"`.
The **floor** parse sits outside the `try`, so a declaration that passed
`validate_semver` at registration raises `ValueError` mid-admission on the serve
path — a broken-deployment error surfacing at the wrong boundary. Separately a
legitimate `1.2.0-rc1` **child** is silently refused as `version-incompatible`.

### F11 · A governance failure collapses into a generic token on a spelling · **LOW**
*Raised by cursor and gemini as "dead vocabulary tokens"; **both verifiers
refuted that framing** and found something real underneath.*

**What was refuted.** `unauthorized` is *not* a door that never opens. A
verifier drove it end to end through the real entitlement path —
`entitled_perspective` → `SubjectUnavailableRefusal(cause="unauthorized")` →
`ChildAdmissionRefusal(reason="unauthorized")` → `compose_children` writes a
validated row with `outcome_status='unauthorized'`, and a required slot refuses.
The assembler translating a child door's refusal is the intended writer.

**What is real.** `ChildAdmissionRefusal.reason` is a **bare `str` with no
closed-vocabulary validation**, and `_status_for`'s fallback maps any
unrecognized reason to `rejected-at-admission`:

```
reason='unauthorized'   -> outcome_status='unauthorized'
reason='unauthorised'   -> outcome_status='rejected-at-admission'   <- British spelling
reason='not-authorized' -> outcome_status='rejected-at-admission'
reason='UNAUTHORIZED'   -> outcome_status='rejected-at-admission'
```

**A governance failure is preserved or silently downgraded depending on an
undocumented spelling convention**, and the SDK ships no helper to map a child
door's refusal into the vocabulary. That is the collapse the closed vocabulary
exists to prevent, arriving through an unvalidated string.

**Two tokens genuinely have no originator:** `refused`, and
`ambiguous-producer` — the latter cannot appear in a row *at all*, because
`resolve_producing_grant` raises rather than returning an outcome.
`record.py:208-212` names *"a governed refusal"* as one of the four absences
that must stay distinct.

And the sharpest instance: the **natural** handling of `AmbiguousProducerError`
— catch it, pass no outcome for that class — records both the row and the
composite refusal as `no-producing-skill`:

> **two producers for one class, logged as no producer.**

### F12 · Duplicate requirements at runtime, and a self-contradicting record · **LOW**
*ollama; the verifier found the sharper variant.*

`compose_children` walks the sequence with no `seen` set and never calls
`requirements_declaration_is_coherent`. `[req, req]` yields two byte-identical
rows that change the replay record's content address. Composed debt is
unaffected (`min` is idempotent). The sharper case:

```
required + optional pair naming ONE class:
  row[0] required=True   status=no-producing-skill
  row[1] required=False  status=optional-absent
```
One record asserting two incompatible dispositions of one requirement.

### F13 · An unadmitted object under an optional key is silently composed · **LOW**
*fable alone.*

`compose_children` branches on `AdmittedChild` / `ChildAdmissionRefusal` /
everything-else, and everything-else means *nothing was produced*. A raw
`ContextProductContract` under an optional key is recorded `optional-absent` and
composed at the declared absence cost — no exception, despite the module
promising `ChildAdmissionBypassError` for a caller reaching past the gate. Under
a **required** key it yields a refusal whose reason (`no-producing-skill`) is
factually wrong: a skill did produce something. My test covers only the required
slot.

---

## 4 · Two defects in my own proof machinery

Both found by fable and its verifier. This is the third and fourth instance this
session of my defects landing in verification rather than mechanism.

### V1 · A test that names one thing and measures another
`test_c21_the_four_absences_stay_distinct` docstring:
> "Declared-absent, refused, **ineligible and unauthorized** reach four different
> `outcome_status` tokens"

Its assertion:
```python
statuses == {"optional-absent", "rejected-at-admission", "ineligible", "no-producing-skill"}
```
It asserts `no-producing-skill`, not `unauthorized`. **Design criterion 21 was
never discharged** — and per F4 it could not have been.

### V2 · A subset check that can never fail
The same test then asserts `statuses <= CHILD_OUTCOME_STATUSES`. A subset check
**can never notice a reserved token that nothing emits**, which is precisely the
F11 defect it sits next to.

---

## 5 · REJECTED — four claims killed by one measurement each

Recorded as rejected rather than dropped: an unverified finding acted on is
worse than no review.

| Claim | Raised by | Measurement that refutes it |
| --- | --- | --- |
| `requires` is hash-transparent, so composition rules change without moving the class address | gemini | Transparent **only at the empty tuple**. Adding a child `ca906af3`→`31bb9733`; changing a lane →`8cad222a`; adding a second →`2fe4e658`; swapping →`45c1af76`. All four distinct. |
| `compose_debt_factors` crashes on a `None` factor | gemini | Every supported path refuses `None` — kwargs, `model_validate`, and `model_validate_json` off the wire. Reachable only via `model_construct`, a deliberate bypass inside the trust boundary. |
| Extra JSON members in an eligibility assertion are silently ignored | ollama | `EligibilityAssertion.model_config` is literally `{'extra': 'forbid', 'frozen': True}`, inherited from `CCFContract`. An extra member yields `ChildAdmissionRefusal`. Attribution control: re-declaring with `extra='ignore'` *does* drop it silently — so the refusal is caused by `forbid`. |
| tz-naive vs tz-aware datetimes cause spurious refusals / DoS | ollama | `encode_eligibility_assertion` **raises** on a naive instant; `WireRequest` refuses a naive `asked_at`. A +05:30 producer instant admits (canonical bytes normalize to UTC); microseconds survive. The only reachable mismatch is a peer bypassing the canonical encoder, and refusing it is what D-IMPL-38 requires. |

**PARTIAL — nested-instance revalidation.** A genuine adjacent observation from
the `None`-factor verifier: `CCFContract` does not set `revalidate_instances`, so
a model forged with `model_construct` is accepted unrevalidated by
`DebtAssessment` and `ContextProductContract`, survives `run_gates`, and is
admitted. Only reachable by trusted code deliberately bypassing its own
validator. **Low, and not a composite defect.**

---

## 6 · The underlying mistake — one design error, seven symptoms

F2, F3, F4, F5, F6, F8 and F9 are not seven independent bugs:

> **`AdmittedChild` proves that admission *ran*. It does not carry *what it ran
> against*, and nothing downstream re-binds it.**

The design document argued the opposite — that holding an `AdmittedChild` **is**
the evidence the checks ran, and that this makes composing an unauthorized child
unspellable. The capability object is real, but **unparameterized**: it binds
neither the requirement, nor the tenant, nor the fabric identity, nor the grant,
nor the entities whose eligibility was (or was not) evaluated. Every gap above
is a place where the caller supplies the missing parameter and the gate believes
it.

The recurring signature is sharper than "a missing check": **the record asserts
an authority that never ran.** F3 and F5 both persist
`eligibility_basis='local-register'` for a register that was never consulted;
F4 persists a `grant_hash` nobody verified; F6 persists a fabric claim naming no
fabric. This is an audit-by-construction defect, not only a gate-skip.

**The remedy is structural.** `AdmittedChild` should carry the requirement,
tenant, fabric identity and eligibility scope it was admitted under;
`compose_children` should re-bind against them rather than trusting a mapping
key; and the gate should receive the agent's bound skills so `grant_hash` is
verified rather than transcribed. F1 additionally needs a **ruling**, because
D-IMPL-336 forecloses the obvious fix.

---

## 7 · What the panel did not cover

Stated so silence is not mistaken for coverage.

- **No external reviewer executed the test suite.** The 49 tests in
  `tests/products/test_composite.py` pass, which is exactly how F0, V1 and V2
  survived. Only fable read the tests, on its own initiative.
- **The four briefed-as-known limitations were excluded by instruction** and are
  unchanged: token bypass via `object.__new__`, the unauthored F/C/S mapping,
  JWS signature verification assumed rather than re-proved, and 51
  base-commit test failures.
- **`tests/`, `docs/` and the surface fragment were not in the payload.**
- **No reviewer assessed performance or concurrency.**
- **No fix has been applied.** This document is findings only; the branch is
  unchanged since `2b2770da`.
