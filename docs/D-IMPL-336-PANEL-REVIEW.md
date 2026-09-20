# D-IMPL-336 — cross-AI code review panel

**Subject:** branch `d-impl-336-composite`, tip `2b2770da`, base `main` `374a3600`
**Reviewed:** `src/ccf/products/composite.py` (755 lines), `src/ccf/peering/eligibility.py` (231), and the diff to `skills/catalog.py`, `products/contract.py`, `halflife/debt.py`, `replay/record.py`, `products/gates.py`, `products/refusal.py`, `products/disclosure.py`
**Date:** 2026-09-13 · **Status: NOT merged. CP-14 acquisition still HOLD.**

> **For the independent agents reading this.** Every finding carries the command
> that produced it. Nothing is asserted on a reviewer's say-so: five reviewers
> raised 37 claims, and **four that multiple reviewers agreed on were killed by
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

$ grep -rn "\.requires\b" src runtime --include=*.py   # at commit f3719856
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
`record.py::CHILD_OUTCOME_STATUSES` names *"a governed refusal"* as one of the four absences
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

## 3a · Found by the completeness critic — five more, all measured

### F14 · Three of the four ruled composition laws are unwired · **HIGH**

`composite.py` declares itself the aggregate-product surface `D-IMPL-104`
deferred — and **never imports `ccf.products.composition`**. `compose_lineage`,
`compose_expiry` and `refuse_mixing` already exist and ship; only
`compose_debt_factors` got called.

```
a child expiring at 11:00, composed into a composition whose instant is 12:00
  -> served=True
ChildResolution fields containing "expir": none
```

`CompositionOutcome` carries `factors`, `resolutions`, `refusal` — **no
validity, no lineage**. So `D-IMPL-31`'s TTL floor and mixing-refusal are not
merely uncalled: a caller using the API as designed **cannot compute the floor**,
and replay cannot tell whether it was applied.

### F15 · The one-`as_of` invariant dissolves at the composition · **HIGH**

`admit()` compares each child against the `asked_at` handed to *that call*.
`compose_children` never receives `asked_at`, and `AdmittedChild` carries no
instant — so the invariant is **structurally uncheckable at the place it is
asserted**.

```
two children admitted at 12:00 and 13:00 -> composed, served=True
replay rows carry two different child_asked_at values
two different composition_invocation values -> also compose together
```

This directly contradicts `ChildResolution`'s own docstring: *"Equal to the
composite's `asked_at` on every admitted child — a composite has exactly one."*
And the anti-replay binding survives per child and **dissolves at the
composition**.

### F16 · Nothing on the peered path verifies a signature · **HIGH**

`ProducedElsewhere.protected_header` is a caller-supplied `Mapping[str, object]`.
The sibling `PeeringAdmissionGate` reaches its header only through
`inbound.signed.declared_header()` **after** verification, under the comment
*"the protected header is now authenticated."*

```
caller mints its own assertion naming producer="fabric://any-string-at-all",
checked_at 400 days stale, in a hand-built dict
  -> AdmittedChild  eligibility_basis='producer-attested'
```

**Four of the five bindings compare caller-supplied data to caller-supplied
data** — `assertion.producer` against `candidate.fabric.fabric_id` most plainly.
Only `consumer_scope` and the recomputed content hash are anchored to anything
the caller does not also control. Compounding it: `fabric_id` is a new identity
axis with **no registry behind it** — the gate consults `_registry` for exactly
one thing, the invalidation register, never a trust policy or permitted-producer
set. So *"producer-attested"* attests that two strings the caller wrote agree.

*(This is adjacent to briefed-known K3 but is not K3: K3 assumed the peering
gate verifies the signature before this code sees the header. On this path
nothing does, and the type system cannot carry the evidence that anything did —
`AdmittedProduct` does not expose the verified header, so a caller could not
forward it even if it wanted to.)*

### F17 · Extra `outcomes` entries are dropped silently · **MED**

The mirror of F2. A child under a key naming no declared slot vanishes from both
the arithmetic and the record:

```
{FAMILY: healthy, COVENANT: weak(F=C=S=0.1)} against requirements=[FAMILY]
  -> one row, composed factors (1,1,1)
```

F2 says the key can name the *wrong* slot; this says a key naming *no* slot is
discarded without a word. Both are the same missing reconciliation between the
declared requirement set and the outcome map.

### F18 · The container reinstates the ambiguity its fields were marked to prevent · **LOW**

Every field *inside* `ChildResolution` is marked hash-transparent `False`, on my
own argument that an absent value and a dropped one must not be the same
artifact. `ContentGenerationPath.child_resolutions` is then marked **`True`** at
`()` — so a composite record whose caller dropped all rows hashes
byte-identically to a record with no children. Low only because nothing writes
the field at all (F0).

---

## 4 · Three defects in my own proof machinery

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

### V3 · A vacuous test whose docstring claims the opposite
`test_a_composites_expiry_floor_survives_composition` imports `compose_expiry`
inside its own body and calls it with **two literal datetimes**. It never builds
a child, a candidate, an `AdmittedChild`, or calls `compose_children`. Its
docstring nonetheless says *"the earliest constituent expiry still bounds the
composite, so a composite can never be labelled fresher than its stalest
child."*

**The test would stay green if `compose_children` were deleted** — and per F14
the property it claims is not true of the shipped path at all.

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

## 6 · The underlying mistakes — two, and they explain almost everything

### (a) The trust boundary is drawn at the gate's OUTPUT instead of its INPUTS

The module spends fifty lines arguing that `AdmittedChild` must be a capability
token because *"compose the unauthorized child and filter it afterwards has no
supported spelling"* — and then **accepts every input as an unattested caller
assertion.**

Everything the gate checks lives *inside* `contract`: class, version, instant,
hash, debt. Everything a caller asserts *about* that contract is taken on faith:

| The caller asserts… | and the gate believes it |
| --- | --- |
| which tenant it belongs to | F5 |
| which fabric produced it | F6 |
| which entities it touched | F3 |
| which requirement it satisfies | F2 |
| which grant produced it | F4 |
| which composition and instant it belongs to | F15 |
| whether its "signed" header was ever signed | F16 |

**The gate verifies the child and trusts the context.** Patching these one at a
time yields seven conditionals. The structural repair is that `ChildCandidate`'s
context fields must arrive as *verified values* — a header derived from a
verified envelope, a tenant taken from the gate rather than the contract,
`touched_entities` non-optional — and that admission must **stamp the
composition identity it ran under** so `compose_children` can re-bind it.

### (b) A declaration surface and an execution surface, built as disconnected halves

`RegisteredProductClass.requires` is read nowhere and `register_product_class`
will not accept it. `requirements_declaration_is_coherent` is never called on the
composition path. `child_resolutions` is written nowhere. Two of the eight
`outcome_status` tokens have no originator and `_status_for`'s catch-all demotes
anything it does not recognize, against a `reason` field that is a bare `str`.
And the ruled `compose_expiry` / `compose_lineage` / `refuse_mixing` laws sit
unwired beside the one law that got called.

**The declared vocabulary, the declared requirements and the declared
composition algebra all exist. The shipped path reads none of them.** That is
why nothing outside tests calls `compose_children` at all.

## 6a · Fix interactions — checked, not assumed

- **F5 (tenant) is the safest fix and has an exact precedent.**
  `PeeringAdmissionGate._check_policy_bindings` opens with
  `if product.tenant_id != self._tenant_id: refuse` — *"trust is per tenant"* —
  and that fires for cross-fabric products too, so a peered child legitimately
  claims the *consumer's* tenant. Adding the same line **does not break the
  `ProducedElsewhere` path**, and every contract in the test module already uses
  one tenant.
- **F3 must be fixed in `composite.py`, not the shared gate.**
  `refuse_dependency_invalidation` documents `None → pass` as a deliberate
  compatibility posture for pre-`D-IMPL-334` call sites; tightening it there
  changes `run_gates` for callers that predate the register. Refusing `None` at
  *composite* admission breaks nothing, and `()` already means "touched nothing"
  so the distinct meaning survives.
- **F7's obvious fix breaks the shipped fixture and needs a ruling.** A
  `checked_at <= requested_as_of` ordering check would refuse **every** peered
  test in the tree: the fixture's `checked_at` is `SERVED_AT` (12:30), later than
  `ASKED_AT` (12:00) — *correctly*, since `asked_at` is a reconstruction instant
  that may be historical while `checked_at` is wall-clock. The alternative, a
  maximum age, is a threshold the SDK may not hold under `D-IMPL-38`. Either the
  docstring is corrected to five, or `checked_at` gets a Control-Plane-declared
  bound. **A decision, not a patch.**
- **F6's fix has nothing to compare against.** No fabric-identity concept exists
  anywhere in `src/` or `runtime/`. Fixing it means introducing a new Control
  Plane axis or folding it into the unused `_tenant_id`. Not a one-liner.
- **F2 and F17 are cheap.** `ChildRequirement` is a frozen `CCFContract`,
  value-equal and hashable (verified), so `outcome.candidate.requirement ==
  requirement` works against the fresh-instance pattern the tests use. Rejecting
  unmatched keys is equally cheap — no call site passes a key it does not
  declare.
- **F15's fix is a signature change**, not a patch: `AdmittedChild` must carry
  the `asked_at` and `composition_invocation` it was admitted under, and
  `compose_children` must take them.
- **F1 needs a ruling**, because `D-IMPL-336` forecloses the obvious fix.

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
