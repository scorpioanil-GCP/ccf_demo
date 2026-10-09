# 378-68-b — words only: `SharedOwnerWalkIncomplete`'s docstring says repair 2.4 (b) is not built, and that the walk admits at its bounds

`D-IMPL-378`, lane `378j-fixup` item D: the "j" batch panel's J-WALK-DOC-24B. **No behavior changes.** **SEC-020 stays
OPEN.**

The docstring quoted Dave's repair 2.4 (b), *"Refuse when the shared-owner walk reaches a limit before completing."*,
as the reading behind repair 1.8, without saying that 2.4 (b) itself is not built, so a reader could take the walk to
refuse at its bounds. It does not: a walk cut off at either bound admits the two phases, which the security how-to
(section 4.12) and the controls register already state. The docstring now says so, and names the tests that measure
it. The refusal it documents, a read that raises inside the walk, is unchanged.

## ccf.products.resolver.SharedOwnerWalkIncomplete

- Surface: ccf.products.resolver.SharedOwnerWalkIncomplete
- Public surface: true
- Change type: behavior
- Before: its docstring quoted repair 2.4 (b) ("Refuse when the shared-owner walk reaches a limit before completing.") as read with repair 1.8, and did not say that 2.4 (b) is not built.
- After: unchanged behavior; its docstring says repair 2.4 (b) is not built: a walk cut off at either bound (`SHARED_OWNER_WALK_DEPTH`, `SHARED_OWNER_WALK_OBJECTS`) raises no refusal and admits the two phases, and the walk reaches its reference bound sooner as a service runs.
- Why: `D-IMPL-378`, the "j" batch panel's J-WALK-DOC-24B. Measured by `tests/products/test_q7_shared_owner_bounded_walk.py::test_q7_limit_an_object_one_step_past_the_depth_bound_is_not_seen`, `tests/products/test_q7_shared_owner_bounded_walk.py::test_q7_limit_an_object_reached_after_the_object_bound_is_spent_is_not_seen` and `tests/products/test_q7_paved_road_keeps_answering_as_questions_accumulate.py`.
- Migration: none. Keep the population phase free of anything the subject-keyed phase writes; the walk does not stand in for that past its bounds.
