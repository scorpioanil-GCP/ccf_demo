# 370-25 — SEC-025: a composite child is admitted only for the subject its composite asked

`D-IMPL-370` (and `D-IMPL-368`/`D-IMPL-369`), row `SEC-025`, ruled at Q16 (a)
of `docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md`: *every
child leg returns the subject it answered; the composite refuses by name on any
mismatch, on every leg kind, and the refusal names the leg, not the subject.*

Before this change only the `mcp-product` leg (`D-IMPL-340`) bound a child's
answer to the question asked. A `local-dispatch` or `mcp` child whose own door
answered about another subject composed silently: the door's
`DoorOutcome.answered.subject` was on the wire and
`src/ccf/products/child_resolver.py::_door_outcome` discarded it.

**Residual, disclosed: SEC-025-U1.** A `peered` (A2A) child is still admitted
without subject binding, because its envelope
(`src/ccf/peering/protocol.py::InboundProduct`) carries no question to echo. It
is bound when SEC-022's signed claim set carries the question;
`tests/products/test_composite_child_subject_binding.py::test_a_peered_child_answering_another_subject_is_refused_by_name`
is `xfail(strict=True)` until then.

## ccf.products.child_resolver.GrantBoundChildResolver

- Surface: ccf.products.child_resolver.GrantBoundChildResolver
- Public surface: true
- Change type: reshaped
- Before: the legacy `CompositeChildResolverProtocol` call only; it handed each skill the deployment's `child_arguments` and never knew the subject the composite asked
- After: a new optional `child_questions: ChildQuestions | None` constructor argument and a `resolve_for(...)` method, so it now conforms to `RequestAwareChildResolverProtocol` and `GovernedResolver` hands it the composite's effective request. Each child's question is minted from that request through `child_questions`, and the child's answered subject is held to it. The legacy `__call__` remains and mints no question
- Why: a composite can only refuse a child that answered another subject if it knows the subject it asked, and that subject comes from the composite's request through the deployment's mapping — never from `child_arguments`, which is what the skill was handed
- Migration: supply `child_questions` (the same `ChildQuestions` mapping `QuestionBoundChildResolver` takes). Without it, or through the request-less `__call__`, every `local-dispatch` and `mcp` child is refused `question-mismatch` rather than admitted unbound. A wrapper that implements only `__call__` around this resolver must add `resolve_for` and delegate to it. Disclosed after the close panel (Fable, `D-IMPL-370`): `ChildArguments` carries no request or question, so the local-dispatch and `mcp` legs are now usable only by single-subject composites; a multi-subject composite's local or `mcp` child is refused `question-mismatch` (fails closed).

## ccf.products.composite.ChildCandidate

- Surface: ccf.products.composite.ChildCandidate
- Public surface: true
- Change type: reshaped
- Before: `question_echo` and `answered_question` were populated on the `mcp-product` leg only; nothing carried the question the composite asked
- After: a new `asked_question: ChildQuestion | None = None` member — the question the composite minted for this child. `question_echo` and `answered_question` now carry the child door's echo and answered axes on the `local-dispatch` and `mcp` legs too
- Why: the gate compares the answered subject to the asked one; both halves must reach it
- Migration: a deployment that builds a `ChildCandidate` by hand for a `local-dispatch` or `mcp` child sets `asked_question`, `question_echo` and `answered_question`, or the gate refuses it `question-mismatch`

## ccf.products.composite.CompositeAdmissionGate

- Surface: ccf.products.composite.CompositeAdmissionGate
- Public surface: true
- Change type: behavior
- Before: the subject/question binding was inline in `hold_producer_claims` and ran for `mcp-product` only
- After: one check, `CompositeAdmissionGate.hold_answer_to_question`, shared by every bound leg — `admit` calls it for `local-dispatch` and `mcp`, `hold_producer_claims` calls it for `mcp-product`. A mismatch refuses with the EXISTING reason `question-mismatch` (no new reason is added), and the refusal detail names the leg and never a subject
- Why: one binding, not one per leg, so it cannot be fixed on one leg and missed on another — severing it unbinds every leg at once, which the row's severing (c) proves
- Migration: none for a served answer to the question asked. A consumer counting `question-mismatch` refusals will now see them on the `local-dispatch` and `mcp` legs as well

## ccf.products.child_resolver.QuestionBoundChildResolver

- Surface: ccf.products.child_resolver.QuestionBoundChildResolver
- Public surface: true
- Change type: behavior
- Before: a `ChildQuestion` was minted only for an `McpProductBinding` entry; any other entry was dispatched with `child_arguments` and its answer was unbound
- After: the `ChildQuestion` is minted for every entry, and every non-peered child's answer is held to it
- Why: Q16 (a) — every leg
- Migration: a `child_questions` mapping must return a question for every requirement the agent may acquire, not only its `mcp_product` ones
