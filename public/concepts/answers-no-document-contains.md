# Answers no document contains

One question, asked of a deployment that ships in this repository: *who
ultimately owns this company?* It is an ordinary line in a regulated onboarding
file, and it has an uncomfortable property. For the company in this example the
answer is a figure that appears in none of the records the question is asked
over. It has to be computed, at the instant it is asked, from a graph, under a
policy regime — and then it has to arrive carrying enough of its own provenance
that an examiner can re-derive it a year later.

This page follows that one question and shows what answering it governably
costs. Every figure below is one the deployment's own artifacts declare, and
every mechanism below is the source that actually runs, included into this page
from the example tree rather than described. A reader can check all of it
without taking anything on trust: open the artifact, run the named test, and
watch it go red the moment the claim stops being true.

That is the standard this page holds itself to. **Every claim below is either a
literal include from a source CI already gates, or a fact about the question's
own declared artifacts.** A sentence with neither behind it is an opinion, and
the SDK does not ship those.

## The question

The deployment asks: **who ultimately owns Acme, as of 1 August?** It asks under
a regime whose beneficial-ownership threshold is **25.0%**. That threshold is
jurisdiction-conditioned regulatory policy rather than a property of the
question, so it lives in the deployment's policy bundle; the same question asked
under a different regime returns a different set of people out of the same
graph.

Four facts about the question, each checkable against the artifacts under
`examples/s1-01-hello-context-product/artifacts/`:

- Jane Doe holds **12.0%** of Acme directly.
- She also holds **60.0%** of a holding company, and that company itself holds
  **30.0%** of Acme.
- Her real interest in Acme is therefore **30.000%**, at or above the regime's
  25.0% threshold. She is a beneficial owner, and an onboarding file that omits
  her is wrong.
- **No record in any source system states that number.** It is not a field
  anywhere in the estate the question is asked over. It is a sum over ownership
  paths, and it does not exist until something computes it.

The fourth fact is the one that sets the price. An answer written down nowhere
cannot be looked up; it can only be derived — and a derivation is defensible
only as far as the record of how it was derived.

### The vocabulary the question is asked in

*"Who ultimately owns this company?"* is a question with a vocabulary: which
resolved class counts as a natural person, which class carries a qualified
ownership interest, and which of its attributes carry the owner, the target and
the fraction. In this deployment every one of those terms is a Control Plane
statement rather than a constant in a module. The projection is an interpreter
of the document below; delete it and there is nothing left for the projection to
compute.

What is deliberately absent from the document is the subject. Which company is
being asked about, and when, arrives on a typed request and is validated at the
door — which is what makes the product something a caller invokes rather than
something an operator configures. A regression there goes red on
`tests/examples/test_s1_01_output.py::test_the_product_answers_the_question_the_caller_asked`,
which checks the served subject, both instants, the perspective role and the
threshold against the request and the scenario rather than against any stored
answer:

```yaml
--8<-- "examples/s1-01-hello-context-product/artifacts/ubo-question.yaml"
```

### The answers the deployment declares

The deployment also declares what its own question should return, in a document
the output test reads so that its expectations come from somewhere other than
itself. Two tests hold the answer.
`tests/examples/test_s1_01_output.py::test_the_aggregate_ownership_answer_matches_the_declared_expectation`
compares the served per-party percentages and the served beneficial-owner list
against this declaration, in order.
`tests/examples/test_s1_01_output.py::test_the_answer_is_a_sum_over_paths_not_a_single_hop`
fails in the one case worth catching: the declaration names a boundary-case
party whose stake one hop down is exactly the regime's threshold and whose
interest in the subject three hops down is a fraction of a percent, so a reading
that walked the chain once would put her at the threshold and wrongly inside the
answer.

The document is included whole rather than sliced. It is this page's answer key,
and it declares more than the ownership figures: what survives each of the four
operator categories, which references were removed and by which operator, the
near miss, the answers to two further questions asked of the same class, the
routing state the deployment expects its own debt calibration to land in, and
the obligation each of those states puts on the answer.

```yaml
--8<-- "examples/s1-01-hello-context-product/artifacts/expected.yaml"
```

## What a governed answer has to do

Three obligations follow from the fourth fact above, and each one is visible in
the example's call spine. The spine holds the fabric calls and nothing else — no
entity class, no source system, no identifier, no threshold, no policy version
and no query — so what follows is mechanism rather than this deployment's
domain.

### It is computed, from artifacts, over a graph at a named boundary

The answer is derived at a temporal boundary the deployment names, and the four
operator categories that derive it are built from the deployment's own parameter
artifacts rather than from anything in the spine. The graph view is taken at that
boundary first and handed to the chain, because the similarity corpus is read out
of the graph at the boundary rather than lazily at first invocation — a corpus
read later would be a corpus read at a different moment than the one the answer
claims.

Each operator leaves a witness the deployment declares. A jurisdiction-restricted
party substituted out, a screening candidate below the similarity floor, an edge
type the traversal was never given, an observation not yet legally effective at
the boundary: if any of those references surfaces anywhere in the served payload,
the operator named beside it has stopped working, and
`tests/examples/test_s1_01_output.py::test_every_declared_absence_really_is_absent`
goes red against the serialized payload rather than against one field.

The operator chain is not built by hand here. Every parameter it runs under —
the jurisdictions, the similarity floor, the edge types, the effectiveness rule
— is authored in `artifacts/operator-parameters-*.yaml`, and the deployment
names those four documents. Naming them is the whole of the wiring; the SDK
resolves the chain from the declarations, which is why no threshold and no edge
type appears anywhere in the example's code.

```py
--8<-- "examples/s1-01-hello-context-product/spine.py:govern"
```

### Which company, and when, is the caller's question — not the fabric's configuration

The subject is not a setting. It arrives on the request, and the request's
subject *seeds the traversal*, which is what puts the subject inside the compiled
graph query and therefore inside the pins the replay record keeps. Before that
was true, two questions about two different companies pinned identically — the
record could not tell them apart. The projection plan is a named local for a
related reason: the binder has to be handed the same object the engine will run,
and a disagreement between the projection's own `projection-requirements.yaml`
and the product class's declared operator keys refuses there, before anything is
assembled, by refusal rather than by repair.

Two tests hold this.
`tests/examples/test_s1_01_output.py::test_a_different_company_gets_a_different_answer`
asks the same class about a company one step up the same ownership chain and
fails if the two answers name the same people — one graph, one ingest, no second
query.
`tests/examples/test_s1_01_output.py::test_the_same_company_at_a_later_instant_gets_a_different_answer`
re-asks the first question at a later boundary against a graph nothing was added
to in between, and fails if the party the declaration says should appear does
not: a share transfer recorded before the first boundary and legally effective
after it is invisible in one answer and decisive in the other.

Both properties are structural rather than diligent. The subject seeds the
traversal because the request carries it into the compiled query, and Π arrives
as a *class* the fabric constructs rather than an object handed over
ready-made — `plan_factory` in the `govern` region above — so the binder that
holds the projection's authored operator set against the product class's claim
can be shown the object it binds. A plan handed over ready-made is a plan no
binder can be shown to have been given.

### The decision is recorded before it is delivered, and every pin resolves

Delivery is what the successful append returns. There is no branch that reaches a
served product without a recorded decision, so an unrecorded answer is an answer
that was never served. The questions actually put to the graph are pinned by
content hash rather than described, and the canonical query bytes land in the
store *before* the record is appended — so no moment exists at which a recorded
pin dangles and nothing can resolve it.

What the decision was obliged to do is recorded the same way, in the record
itself rather than as a pointer at the profile that bound it, so that editing the
profile tomorrow cannot rewrite what yesterday's answer was obliged to do.
`tests/examples/test_s1_01_output.py::test_the_obligation_in_force_is_pinned_into_the_replay_record`
checks the obligation on every answered question against the one the product
carries, and the third question's against the deployment's own declaration.

None of that is code in this example any more. The three L6 gates, the
five-dimension record, the query pins, the persisted append and the delivery are
one object the SDK owns, reached by the single `build_governed_resolver` call in
the `govern` region above — which is what makes "there is no branch that reaches
a served product without a recorded decision" a property of the fabric rather
than a property of this deployment having remembered to write one.

## Two supported ways to produce, and what each carries

Both routes to a governed product are supported at launch, and they are two
routes rather than one with a shortcut.

**The paved road** — `open_product` over two documents — binds a deployment's
acquire, project, assess and gate callables to its declarations and owns the
whole governed spine: request resolution, operators, the three gates, the
five-dimension record, the append and the delivery. It does not cover a
**post-traversal deterministic aggregation** — a computation that must run after
the declared traversal and before the projection, as an exposure roll-up's
gross-and-adjusted determination does. The road's vocabulary has no declared
home for that step, and it is not a step this page invents.

**Lower-level governed assembly plus the standard door** is the supported path
for that shape: the deployment orders its own aggregation, then reaches the
same one governed object through `build_governed_resolver`, and serves through
the same door. The record, the gates and the delivery are the SDK's on both
routes; what differs is who orders the steps before governance.

On the lower-level route, **an ordinary fault stays a fault.** A `ValueError`,
a `TypeError`, a `LookupError` or an `OSError` inside a deployment's assembly
is answered at the door as an opaque runtime failure, never dressed as a
business refusal. The one explicit handoff for a refusal the fabric has already
made — a determination the deployment holds and cannot return from where it
was made — is `GovernedRefusalRaised`, which carries that refusal and its
resolution state to the boundary that records and delivers it. Supporting the
route does not authorize converting arbitrary exceptions into refusals, and
nothing in the SDK does so on a caller's behalf.

One consequence is stated rather than left to be found: on the lower-level
route, a request-contract violation that surfaces **before** acquisition — the
effective request resolved ahead of the read, as an exposure walk must — is
raised as an exception and reaches the door as a runtime failure with no
governed envelope and no replay record. That is a recorded limitation of that
route, not of the paved one.

### Reconstructing what either route served

A served product or a governed refusal is reproduced from its record and the
store through the SDK's engine — [Reconstruct a governed determination][recipe]
is the supported recipe. It supplies an environment of three methods, calls no
producer, invokes no question mapping, and names the one private call it
makes.

### Limitations, stated as limitations

These hold on the current baseline and are not lifted by the shipped examples
passing:

- **Observation reduction can use two instants.** The freshness factor reduces
  the observation set as of the view instant while the evidence anchor reduces
  it as of the decision instant. They coincide for every shipped class and
  diverge only for a class that combines an evidence anchor with a declared
  decision-instant parameter, which none does.
- **The replay hold takes the declared anchor basis from the rehydrated
  declaration**, not from a basis pinned in the record.
- **Refusal records do not pin the half-life table.**
- **A composite whose child's expiry is itself the binding floor** has no
  dedicated control; the parent-binding case and the floored case do.
- **The registration guard against an unpinnable evidence clock is defensive**:
  no configuration reachable today can declare one, so the guard has no control.

## The three approaches this is usually compared against

An adopter weighing this deployment against something else is usually weighing
it against one of three things: RAG over a vector store, hand-rolled context
assembly, or a semantic layer plus prompt templates. Those three are what this
section is about, and there is no fourth.

The method here is fixed, and it is this page's contract with its reader. Each
of the three gets a subsection; each subsection states what the UBO question
demands — checkable against the artifacts included above — and then what this
deployment does about it, cited to the mechanism that actually runs. Setting
those two beside each other is the whole of the argument, and the comparison is
the reader's to draw rather than this page's to assert. Nothing below states a
limit of another approach as a bare assertion: that would be a claim with
nothing behind it to open, and this page does not make one.

### RAG over a vector store

Start from the fourth fact above. The figure the question returns is written
down in no record anywhere in the estate the question is asked over. It is a sum
over two ownership paths — 12.0% held directly, plus 60.0% of a holding company
that itself holds 30.0% of Acme — and
`tests/examples/test_s1_01_output.py::test_the_aggregate_ownership_answer_matches_the_declared_expectation`
is what holds the served figure to the deployment's own declaration, per party
and in order. What holds it to being a *sum* rather than a *hop* is the
boundary case:
`tests/examples/test_s1_01_output.py::test_the_answer_is_a_sum_over_paths_not_a_single_hop`
takes the one party whose stake a single hop down is exactly the threshold and
requires her reported interest to land strictly below it.

Three further facts about the same question, each of them a different answer out
of the same graph. The same product class asked about Beta Holdings — one step up
Acme's own chain, so the same graph read from a different anchor — puts Jane Doe
at 60.000% and John Smith at 0.000%, which is a different list of beneficial
owners;
`tests/examples/test_s1_01_output.py::test_a_different_company_gets_a_different_answer`
holds that. The same class asked about Acme again six weeks later, against a
graph nothing was added to in between, puts a third person in the answer,
because a share transfer recorded before the first boundary became legally
effective after it;
`tests/examples/test_s1_01_output.py::test_the_same_company_at_a_later_instant_gets_a_different_answer`
holds that one. One graph, one ingest, three answers, and each of the three is
the right answer to the question it answers.

The mechanism that computes them is the projection stage of the call spine,
included above: the request's subject seeds the traversal, the graph view is
taken at the boundary the request names, and the aggregation runs from there.

### Hand-rolled context assembly

This contrast is about the seam rather than about the graph behind it, so it is
cited against the client surface rather than against the example above.

A program consuming a Context Product reaches it through
`src/ccf/client/client.py::ProductClient`, addresses it through
`src/ccf/client/binding.py::resolve_binding`, and receives
`src/ccf/client/result.py::Result` — a typed payload, the measured Context Debt
in force when the answer was assembled, the content address, the lineage and the
replay reference, or an explicit refusal carried as a value rather than raised.
When the wire never spoke at all, `src/ccf/client/errors.py::TransportError`
says so, and that distinction is the taxonomy's whole point: a refusal is the
fabric working, an exception is the fabric never having been reached.

Three facts about that seam, each one held by a test. The reader-visible entry
modules of `examples/hw1-companies-over-revenue` import nothing from `ccf`
beyond that surface, and the three foreign-harness clients under
`examples/hw1-harness-clients` import nothing from `ccf` at all — that root
refuses the package by name. Both are asserted as an AST property of the
modules sitting *directly* in each example root by
`tests/examples/test_client_example_purity.py::test_the_client_example_imports_only_the_client_and_stdlib`.
Each root's producer-side code — the deployment, the server, the runner — lives
one directory down and is deliberately outside that gate, because it is the
producer's world and imports the fabric legitimately.
The same consuming program run over two different transports returns the same
content address, held by
`tests/examples/test_hw1_two_transports.py::test_both_documented_transports_return_the_same_answer`.
And the two transports really are two rather than one wearing two names, held by
`tests/examples/test_hw1_two_transports.py::test_the_two_documented_transports_are_actually_different`.

**Why the citations in this subsection are prose and not includes, stated rather
than left to be inferred.** No file under `src/` carries a snippet section
marker, and neither of the two `hw1` trees carries one either, so an include
against the client seam is not a form that exists to be chosen — it is not a
form this page looked at and declined. The citations are checked all the same:
every `path::symbol` node id above is resolved by this repository's citation
lint under its `cite03-node-id` rule, which goes red the day a cited file stops
defining the symbol named. This page's include obligation is discharged by the
five literal includes carrying the `s1-01` demonstration, which is where its
code-backed claims about the fabric live.

### A semantic layer plus prompt templates

The question's vocabulary is a Control Plane statement, and the artifact holding
it is included above. Which resolved class counts as a natural person, which
class carries a qualified ownership interest, and which of that class's
attributes carry the owner, the target and the fraction are all declared there
and interpreted by the projection at assembly time. Nothing in the deployment's
code carries the question's words: the projection is an interpreter of that
document, and deleting it leaves the projection with nothing to compute.

What is deliberately absent from the document is the subject. Which company is
being asked about, and as of when, arrives on a typed request and is validated
at the door against the product class's declared request contract — which is
what makes the product something a caller invokes rather than something an
operator configures. `tests/examples/test_s1_01_output.py::test_the_product_answers_the_question_the_caller_asked`
checks the served subject, both instants, the perspective role and the threshold
against the request and the scenario rather than against any stored answer.

The threshold is somewhere else again. It is jurisdiction-conditioned regulatory
policy rather than a property of the question, so it lives in the policy bundle,
and the same question asked under a different regime returns a different set of
people out of the same graph.

## What this deployment measures about its own answer

An answer that was right six weeks ago is not the same asset as an answer that
is right now, and this deployment measures the difference rather than asserting
it. Question 1 and question 3 of the expectation included above are the same
question about the same company, asked at two instants against the same graph
with nothing ingested in between. The declaration states which routing state the
deployment expects its own calibration to put each of them in:
`debt_signal_first_question` is `ok`, `debt_signal_third_question` is
`forced_llm`. The later question crosses this deployment's Forced-LLM band.

The declaration also states which factor moved. `debt_weak_factor` is
`freshness` — completeness and semantic consistency stay where they were — so an
examiner reading the assessment can see which of the three dimensions collapsed
rather than only that the debt rose. And `obligation_first_question` and
`obligation_third_question` state what each routing state puts on the answer:
the first is the SDK's named sentinel for a state its calibration deliberately
leaves unbound, the second is this deployment's own sentence, quoted from its own
calibration artifact. The obligation the consumer reads is byte-identical to the
string in `examples/s1-01-hello-context-product/artifacts/debt-profile.yaml` —
`tests/examples/test_s1_01_output.py::test_the_routing_state_carries_what_this_deployment_says_it_obliges`
compares the two — so the SDK supplied the binding and the carrying, and the
deployment supplied every word.

Three tests hold this.
`tests/examples/test_s1_01_output.py::test_the_debt_figure_is_measured_and_not_constant`
is the one a runner goes red on if the crossing stops happening: it asserts that
the later question measures strictly more debt than the earlier one, that the
two routing states are the two the declaration names, that the weak factor falls
between them, and that the other two factors do not move at all.
`tests/examples/test_s1_01_output.py::test_the_delivered_product_carries_its_debt`
holds that the debt rides the delivered product — a first-class decision input
for the consumer, rather than a log line read afterwards.
`tests/examples/test_s1_01_output.py::test_the_routing_state_carries_what_this_deployment_says_it_obliges`
holds both obligations, and holds that the two differ.

What those tests assert is the band crossing and the direction the freshness
factor moves. They do not assert any particular Context Debt figure, so this
page states none. The figures are a decay computation over the assembled view,
and the deployment declines to declare them for the reason its own expectation
document gives: restating them there would be authoring the answer the
computation exists to produce. The band names, the weak factor and the two
obligations are the claim; the arithmetic behind them belongs to the run.

## Where a document search is stronger, and this is not

The lineage entry a Context Product carries has a `passage_anchor` field, and the
contract behind it ships: `D-IMPL-46` rules the `PassageCitationProvider`
Protocol, and `src/ccf/contracts/claims.py::PassageAnchor` is the typed anchor
that field takes (whitepaper §7.10.3). Pattern 5, unstructured ingestion, was
never built, so no shipped pipeline produces passage anchors from documents.
What the lineage on this page's answer anchors is the source identity and the
observation envelope each ownership claim arrived on, accumulated by set-union
across corroborating sources — which is what this question needs, and it is a
different thing.

Extractive provenance over a document corpus is the one place on this page where
a retrieval system does something this deployment does not do, and the page says
so rather than routing around it: a comparison that implied otherwise would
overclaim at exactly the point where it is most exposed. What is claimed here is
narrower, and it is the whole claim. The answer is computed from a graph at a
named boundary, under a policy regime, with the operators that shaped it and the
obligation in force recorded before it was delivered — and the price of that is
that its provenance points at observations and source systems rather than at
sentences.
[recipe]: ../how-to/reconstruct-a-governed-determination.md
