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
