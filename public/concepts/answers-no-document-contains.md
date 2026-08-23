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

```py
--8<-- "examples/s1-01-hello-context-product/spine.py:operators"
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

```py
--8<-- "examples/s1-01-hello-context-product/spine.py:project"
```

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

```py
--8<-- "examples/s1-01-hello-context-product/spine.py:serve"
```

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
`tests/examples/test_s1_01_output.py::test_the_answer_is_a_sum_over_paths_not_a_single_hop`
is what holds it to being a sum rather than a hop.

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

Three facts about that seam, each one held by a test. The consuming programs
under `examples/hw1-companies-over-revenue` and `examples/hw1-harness-clients`
import nothing from `ccf` beyond that surface, asserted as a property of their
import trees by
`tests/examples/test_client_example_purity.py::test_the_client_example_imports_only_the_client_and_stdlib`.
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
