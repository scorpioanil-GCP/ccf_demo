# CCF Example Evaluation Criteria

**Normative repository policy.** This document defines how every current and
future CCF SDK example under `examples/` is designed, evaluated, reviewed, and
classified, with the SDK's viability, correctness, consistency, replayability,
developer friction, and launch readiness as the primary objectives.

It is loaded by `CLAUDE.md` §9 ("Example Development and Evaluation —
REQUIRED") and applies throughout example development — at design, while
building, at review, and at close — not only during final review. It governs
examples going forward and examples in progress. It does not rewrite
historical findings, specifications, gate records, or rulings; those remain
historical evidence in their own vocabulary.

It is one document, in one place. Other documents point here; none restates
it. The example delivery recipe (`public/reference/specifications/
example_delivery.md`) governs the mechanics of shipping an example; this
document governs what an example is *for* and how what it finds is judged.

If an example-specific instruction conflicts with this policy, **stop and
surface the conflict** rather than silently overriding the policy.

---

## A · Purpose and governing principle

**CCF examples are SDK proving grounds, not the product being shipped.** The
product is the SDK. An example exists to put a realistic, governed question
through the SDK's public surface and to report, honestly, what the SDK did.

**The engineered estate and scenarios exist to exercise realistic
conditions.** The curated stores, the synthetic filings, the roster of
obligors and facilities, the pinned instants — all of it is scaffolding built
so that the SDK meets conditions a real deployment would meet. None of it is
the deliverable, and none of it is to be tuned until an example looks good.

**The primary question every example answers:**

> Can the SDK consistently, accurately, governably, and replayably provide the
> capability this example represents?

**The secondary question:**

> Can the engineered example credibly demonstrate that capability?

The order matters. An example that answers the secondary question and not the
primary one has demonstrated the example, not the SDK.

Two consequences follow, and both are load-bearing:

- **A governed refusal may be a successful SDK demonstration.** A product
  withheld above the caller's tolerance, a child refused on its own declared
  gate, a request refused by name with a replay reference — each of these can
  be exactly what the SDK is supposed to do. A red run is not a failed
  example until its cause is classified.
- **A successful-looking example that depends on bespoke workarounds may
  represent an SDK failure.** A green example whose spine hand-composes a
  seam the SDK owns, writes a value over a resolved Control Plane artifact,
  reconstructs child-owned data from raw stores, or carries glue that every
  adopter would have to re-write is evidence of a missing or wrong SDK
  capability, however clean its output.

---

## B · Finding classification

Every material issue discovered while building, reviewing, or closing an
example is classified **before remediation** as exactly one of the four
categories below. Classification is the first act after measurement and
precedes any fix: fixing first and classifying afterwards converts SDK
evidence into example repairs and loses the finding.

### 1. LAUNCH-BLOCKING SDK CAPABILITY

A capability the SDK's core Context Product contract requires and the SDK
does not provide, or provides incorrectly. Without it, CCF cannot honestly
claim to deliver the contract (see §D).

Representative examples: a composite cannot admit a child produced under
another tenant at all; a served product's lineage cannot be reconstructed
from its replay record; a refusal is served as a product; a required child is
silently replaced by an empty one; a consumer must import a producer's
assembler because the SDK cannot consume the producer's product.

### 2. LAUNCH-BLOCKING SDK ERGONOMICS

The capability exists, but the supported path to it creates enough friction
or misuse risk that adopters would predictably work around it, duplicate it,
or get it wrong (see §C, step 2). Ergonomics is launch-blocking only when the
alternative materially undermines adoption or invites misuse.

Representative examples: a value that must be stated in two authorities that
can drift apart; a failure that surfaces only at serve time as an opaque
runtime id when it could have been refused at boot by name; a wiring that
works only when the adopter knows an SDK-internal ordering rule nothing in
the public surface states.

### 3. POST-LAUNCH SDK ENHANCEMENT / ADOPTION FEATURE

A capability or convenience that would make the SDK easier or broader to
adopt, that the launch contract does not require, and for which a supported
path exists today. Recorded as a backlog requirement (§I), never implemented
opportunistically inside the example that surfaced it.

Representative examples: a generalized parameterized-product framework;
discovery over intents and capabilities; fan-out helpers for asking one
producer several questions; templates for common product shapes; richer
diagnostics for a refusal an adopter can already read from its record.

### 4. EXAMPLE / ENGINEERED-ESTATE LIMITATION

A property of the engineered data, the pinned scenario, or the example's own
design — not of the SDK. It is recorded and disclosed where a reader will meet
it, and it is never "fixed" by tuning the SDK's behavior or the example's
governed values.

Representative examples: a snapshot estate whose newest filing is older than
a declared window at the demonstration instant; a synthetic cohort with no
peers for a SIC code; an obligor with zero rows on a required leg; a
demonstration instant held to a pin another example set; high Context Debt
that is the honest reading of thin data.

### The rule

A finding lives in exactly one category. When a finding seems to straddle two
— the SDK provides the mechanism but the estate cannot exercise it — record
both halves as two findings, each in its own category. Do not average them
into a softer one.

---

## C · Launch decision test

Every finding classified as an SDK matter (categories 1–3) is placed by the
following two-step test, applied in order and recorded with its answer.

**Step 1.** *Could we ship the SDK without this capability and still honestly
claim CCF provides its core Context Product contract (§D)?*

- **No** → **launch blocker** (category 1). Stop the example under §J and
  raise the finding for a decision.
- **Yes** → continue to step 2.

**Step 2.** *Would the supported alternative create enough friction or misuse
risk to materially undermine adoption?*

- **Yes** → **candidate launch ergonomics blocker** (category 2). Raise it
  with the friction measured (§E), for a decision; it is not a blocker until
  ruled one.
- **No** → **backlog enhancement** (category 3). Record it under §I and
  continue on the supported path.

The test is asked about the SDK's contract, never about the example's
convenience. "This example would be shorter" is not a step-2 yes. "Every
adopter would have to write this, and half of them would write it wrong" is.

---

## D · Core launch contract

The capabilities the examples collectively prove at launch. **Not every
example must independently prove every item**; the ladder as a whole
establishes them, and each example states which items it exercises.

The SDK must let a deployment:

- **define** Context Product contracts — class, lane, request surface, TTL
  anchor, obligations, declared gates — as Control Plane artifacts;
- **assemble** products from governed source reads through the single write
  handle and the declared operators;
- **consume** independently produced products without importing their
  producers;
- **acquire** products through supported skill and provider mechanisms —
  local callables, fixed MCP resources, parameterized `mcp_product`
  producers, peering — by governed grant;
- **apply authorization and policy before use** — entitlement, the policy
  envelope, the effective request — so that nothing inadmissible is ever
  materialized;
- **preserve product identity and content addressing** — the same question
  hashes to the same bytes, whatever transport carried them;
- **calculate Context Debt correctly** — `D_c = 1 − F·C·S` over what was
  assembled, per the declared λ_c and decay basis, aggregated by the ruled
  laws;
- **compose** Context Products — a composite declares the classes it requires
  and admits governed children;
- **propagate lineage and expiry according to declared SDK semantics** —
  lineage by set-union, expiry by the declared anchor and the composite floor,
  and where the SDK's behavior departs from a declaration the departure is a
  recorded finding, not a silent difference;
- **refuse correctly** — the right reason, by name, as data, with a replay
  reference, and never a raise where a governed refusal is owed;
- **preserve sufficient refusal evidence** — an examiner can tell from the
  record *why* a product or a child was refused, not only that it was;
- **replay and reconstruct** governed decisions from the record and the
  store, with no second producer call and no invented input;
- **support local and remote producer boundaries** — the same product
  consumed in-process and across a deployment boundary, with the boundary
  visible in the record;
- **prevent tenant, product, and provider identity confusion or
  masquerading** — a producer's claim about itself never authorizes; equality
  with a governed registration is a binding check.

An example that cannot exercise an item it set out to prove records why
(§B.4 if the estate is the reason; §B.1 if the SDK is).

---

## E · Developer-friction evaluation

**Every example evaluates how difficult the SDK was to use, not merely
whether it eventually worked.** A capability that exists behind three
undocumented steps and a copied helper is a friction finding even when the
example is green.

Capture, where relevant, with the count or the shape rather than an adjective:

- **product registration and configuration** — how many documents, keys, and
  restatements one product needed;
- **skill grant configuration** — what an agent needed to hold a grant, and
  whether the policy regime, catalog entry, and grant agreed by construction
  or by care;
- **producer registration** — what a consumer had to declare to reach a
  producer, and where the endpoint and credential actually came from;
- **argument mapping** — how the composite's effective request became the
  child's question, and whether that mapping had one home;
- **custom adapter or glue code** — every function the example wrote that a
  second example would have to write again;
- **SDK-internal knowledge required** — ordering rules, sentinel values,
  timestamp semantics, and defaults that nothing on the public surface
  states;
- **duplicated configuration authorities** — one number or name stated in two
  places that can disagree;
- **failure timing and diagnostic quality** — whether a mistake was refused
  at boot by name, at serve as a governed refusal, or at serve as an opaque
  runtime failure;
- **amount of bespoke plumbing** — lines of code in the example that are
  neither domain vocabulary nor a call an adopter must make.

**The target developer experience**, stated conceptually, is the chain:

> requires → skill grant → producer registration → argument mapping →
> governed child

A parent declares the class it **requires**; an agent holds a **grant** for
a skill that produces it; the deployment **registers** the producer that
serves it; the deployment states how the parent's question **maps** to the
child's; and the SDK returns a **governed child** or a governed refusal. Every
step an example needs beyond that chain is friction to name.

**Repeated friction is evidence.** One example writing a helper is a note.
Three examples writing the same helper is the case for a reusable SDK
abstraction (§H), and the examples are where that case is built.

---

## F · Launch versus backlog discipline

**Useful features are not automatically launch requirements.** The
distinction to hold is between:

- the **minimum reusable mechanism required for launch** — what the core
  contract (§D) needs, in a form an adopter can use without re-implementing
  it; and
- a **generalized adoption or ergonomics capability that can ship later** —
  what would make the mechanism broader, easier, or more discoverable.

**Parameterized Context Products are the representative case.**

- Enough governed parameterization for the actual launch scenarios may be
  required: a parent must be able to ask a producer a *question* — a subject,
  an instant, an intent, parameters — and admit the governed answer under
  the producer's tenant. That is mechanism, and its absence was a launch
  blocker when it was found.
- A generalized parameterized-product framework — product templates,
  discovery by intent and capability, dynamic request schemas, fan-out
  helpers that ask one producer many questions, question builders that
  derive a child's parameters from a parent's schema — may be post-launch.
  Each is recorded under §I with its evidence.

**Do not automatically implement the generalized feature.** The example that
surfaces the need records it; a decision funds it; the SDK phase that builds
it is its own phase with its own review.

---

## G · Product specificity

**Similar business products may legitimately be different Context Product
classes.** For example:

- Commercial Credit Memo Context
- Equipment Finance Credit Memo Context
- Specialized Industries Credit Memo Context

These may share structural patterns — a composite over an obligor, a spread
child, a collateral child, a policy envelope — while differing in their
calculations, their evidence, the children they require, the policies in
force, their debt semantics, and how they are assembled. Those differences are
the product, not noise around one product.

**The parent declares the specific product class it needs.** `requires`
names a class and a compatible lane, never a producer, a skill, a tenant, or
a transport. **The skill and provider mechanism determines how that class is
obtained** — which registered producer, under which grant, across which
boundary.

**Do not prematurely collapse domain products into one universal class.** A
"universal credit memo" whose payload is a union of every variant's members,
or a parent that requires a base class and hopes the right variant arrives,
trades the specificity the contract exists to carry for a smaller registry. If
two products are the same product, one class serves both; if they are not,
two classes do, and the composition mechanism is what keeps that honest.

---

## H · Avoid over-generalizing from one example

**A requirement exposed by one example does not automatically justify an
SDK-wide abstraction.** One rung's need is one data point about the SDK. It
earns a finding, a backlog record, and a supported path; it does not by itself
earn a new surface.

**Repeated evidence across examples raises the case for generalization.** When
a second and a third rung meet the same need and write the same glue, the
backlog record's priority rises (§I) and the abstraction becomes a candidate
for its own decision — with the repeated examples as its evidence.

**Facility-level versus obligor-level collateral is the representative
pattern.** One rung needed collateral at the *facility* grain and the SDK's
supported path answered at the *obligor* grain; the right move was an
explicit facility identifier in that rung's request, not a general "grain
selector" bolted onto every product. If later rungs need the same grain
distinction on other products, that repetition — not the first rung — is the
case for a general mechanism.

---

## I · Backlog requirements

Every deferred SDK enhancement (§B.3, and any §B.2 finding not ruled a
blocker) is recorded as a **backlog requirement** with these fields, each
filled:

| field | what it holds |
|---|---|
| **capability** | what the SDK would provide, stated as a capability rather than a design |
| **evidence / rung(s)** | which example(s) surfaced it, with the finding ids |
| **current supported path** | how an adopter achieves the outcome today, exactly |
| **friction** | what the supported path costs, measured per §E |
| **adoption impact** | who is affected and how — which adopters, which products |
| **launch necessity** | the §C answers, with the reasoning |
| **scope / risk** | what building it touches, and what it could break |
| **recommended release** | when it should ship, relative to launch |

**Deferred findings must remain visible.** A backlog record lives where the
next example's author will read it before designing, and it is never closed
by silence. **Repeated evidence raises priority:** each additional rung that
meets the same need is added to the record's evidence and moves its
recommended release earlier.

---

## J · Stop conditions

**Example implementation must stop — and the finding be raised for a decision
before any further building — when a reusable SDK capability is missing or
incorrect.** Concretely, stop on any of:

- **materially incorrect governance** — a policy envelope, entitlement, or
  effective-request resolution that admits what it should refuse or refuses
  what it should admit;
- **replay failure** — a governed decision that cannot be reconstructed from
  its record and the store, or that reconstructs to a different address;
- **identity or provenance confusion** — a product, tenant, or producer
  identity that can be claimed rather than established, or a guarded path
  that can be bypassed;
- **a refusal incorrectly becoming a serve** — any path on which a governed
  "no" reaches a consumer as a product;
- **silent replacement of a required child** — an absent, refused, or
  substituted child admitted as if it were the required one;
- **inability to consume a required Context Product** — a parent that cannot
  acquire or admit a class it declares, through any supported mechanism;
- **reconstruction of child-owned data from raw stores** because the SDK
  cannot consume the child — the parent reading the child's tables is the
  defect the composition boundary exists to prevent, never a workaround;
- **substantial repeated bespoke plumbing** indicating a missing reusable
  abstraction — the third example writing the same glue stops and raises it
  rather than writing it a third time.

When a stop condition fires: classify (§B), record, and raise. Do not widen
the example, do not patch the SDK inside the example's phase, and do not
build around the gap.

**What does not, by itself, stop an example:**

- **inconvenient engineered data** — a cohort with no peers, an obligor with
  no rows on one leg, a filer that uses none of the declared tags;
- **high Context Debt** — the honest reading of thin, stale, or partial data
  is a result, not a defect;
- **an honest refusal** — a product withheld above tolerance, or refused by a
  declared gate, is the SDK working;
- **stale synthetic data** — a snapshot estate is older than the instants a
  scenario would like; disclose the calibration where the reader meets it;
- **unattractive scenario results** — a memo that cannot be written, a
  coverage ratio below one, a spread that fails closed;
- **optional convenience features** — anything that would make the example
  shorter without changing what the SDK proved.

These are recorded (§B.4 or §I) and the example continues.

---

## K · Required close-report structure

**Every example's close report distinguishes the following six sections, in
this order, and does not mix them:**

1. **SDK capability proven** — which items of the launch contract (§D) this
   example exercised, with the gates and the measurements that show it.
2. **SDK friction observed** — the §E findings, measured; the target chain and
   where this example departed from it.
3. **Launch blockers** — §B.1 and ruled §B.2 findings, each with its §C
   answers and its decision id.
4. **Backlog candidates** — §B.3 and unruled §B.2 findings, each as a §I
   record.
5. **Estate / example limitations** — §B.4 findings, disclosed where the
   reader meets them.
6. **Product result** — what the example served or refused, with the honest
   numbers, and what a consumer of this product can and cannot rely on.

A report that folds friction into the product result, or a limitation into a
blocker, has lost the distinction this policy exists to keep. Passes,
expected failures, and mutation outcomes are reported separately from one
another and from the count of declared gates; a count of executing gates or of
red mutations is never presented as "every declared property passed."
