# 378-23 (P3) — SEC-020 candidate: the child-arguments mapping is handed the request its children are asked about

`D-IMPL-378`, SEC-020 residual P3 ("child arguments"), built as the design
lane's recommended option (a): *"Hand the child-arguments mapping the asked
request. This is a public type change."* Lane `378d-s020next`. **A candidate:
Dave has not ruled P3**, and the coordinator integrates nothing until he does.
**SEC-020 stays OPEN.**

**What the tests measure, on test fixtures.** In
`tests/products/test_withheld_subject_child_arguments_and_question_stores.py`,
red before the change and green after; handing the mapping the instant again
(one severing) reddened all four.

- The mapping is handed one `ProductRequest` per child, equal to the request
  the deployment's `child_questions` mapping is handed for that child: the
  declared undisclosed subject for a subject the early policy does not
  disclose, the caller's own subject otherwise, at the composite's `asked_at`.
- An early-withholding composite whose mapping reads the child's subject off
  what it is handed asked its child about the declared undisclosed subject,
  and was served or refused exactly as a nonexistent subject's composite was,
  every member but a refusal's own `replay_reference`, on both child anchors.
  Before the change, under `from_decision` the withheld composite was refused
  `composite-child-refusal` where the nonexistent one was served; under
  `from_entity_freshness` both were refused, but the child was asked about the
  withheld subject itself.

**What it does not cover.** A mapping that ignores what it is handed and takes
the subject from state the deployment captured itself still asks the child
about the withheld subject, and the composite is then refused where a
nonexistent subject's is served; the SDK cannot see where a mapping's values
come from. The arguments are still the deployment's to state (`D-IMPL-38`).
Only the subject is replaced: on the fixture, the request a withheld
subject's mapping was handed carried the caller's parameters unchanged, so a
parameter that itself names an entity reaches the mapping as the caller sent
it.

## ccf.products.child_resolver.ChildArguments

- Surface: ccf.products.child_resolver.ChildArguments
- Public surface: true
- Change type: reshaped
- Before: `Callable[[ChildRequirement, datetime], Mapping[str, str]]`, handed the requirement and the composite's `asked_at`; a mapping could learn the composite's subject only from state captured beside the resolver.
- After: `Callable[[ChildRequirement, ProductRequest], Mapping[str, str]]`, handed the requirement and the EFFECTIVE request `resolve_for` is handed (the one `ChildQuestions` mints the child's question from); its `asked_at` is the composite's.
- Why: SEC-020 residual P3. Under the early policy that request names the declared undisclosed subject, so a mapping that reads the subject off it asks the child what a nonexistent subject's composite asks. It also lifts the limit fragment 370-25 disclosed: a multi-subject composite's `local-dispatch` and `mcp` children can now be asked about the composite's own subject without captured state.
- Migration: change `(requirement, asked_at)` to `(requirement, request)` and read `request.asked_at`; take any per-request value (the subject, a parameter) from `request`. In this tree nine mappings in seven test modules moved this way, and no example or `runtime/` module supplies one.

## ccf.products.child_resolver.GrantBoundChildResolver

- Surface: ccf.products.child_resolver.GrantBoundChildResolver
- Public surface: true
- Change type: behavior
- Before: `resolve_for` handed `child_arguments` the requirement and `asked_at`. The request-less `__call__` dispatched every granted child, and the admission gate then refused every bound leg's answer `question-mismatch`, because no question was minted.
- After: `resolve_for` hands `child_arguments` the request it is handed. The request-less `__call__` refuses every granted requirement `question-mismatch` before its skill is dispatched; an ungranted one is still the honest absence `None`.
- Why: SEC-020 residual P3. A request-less call has no request to hand the mapping and no question to hold the child's answer to.
- Migration: none for `GovernedResolver`, which calls `resolve_for`. A caller of the request-less `__call__` gets the same refusal it got for every bound leg, without the child being asked.

## ccf.products.child_resolver.QuestionBoundChildResolver

- Surface: ccf.products.child_resolver.QuestionBoundChildResolver
- Public surface: true
- Change type: behavior
- Before: its optional `child_arguments`, for entries other than `mcp_product`, was handed the requirement and `asked_at`.
- After: it is handed the same effective request `child_questions` is handed.
- Why: SEC-020 residual P3.
- Migration: as for `ChildArguments`.
