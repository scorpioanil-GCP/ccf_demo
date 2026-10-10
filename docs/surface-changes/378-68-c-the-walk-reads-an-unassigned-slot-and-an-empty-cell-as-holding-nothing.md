# 378-68-c — words only: `PopulationPhaseSharesAnOwner` and `SharedOwnerWalkIncomplete` say that a slot never assigned and an empty closure cell are read as holding nothing, and only another raise refuses

`D-IMPL-378`, lane `378j-fixup` follow-up P: the "j" batch panel's J-SP-WALK-READS, which item H corrected in the
security how-to (section 4.12). **No behavior changes.** **SEC-020 stays OPEN.**

`PopulationPhaseSharesAnOwner`'s docstring said that where reading what an object holds raises, the walk cannot
complete and the two phases are refused. `SharedOwnerWalkIncomplete`'s named a declared slot never assigned, but not an
empty closure cell, as read as holding nothing, and fragment `378-63-a`'s entry for it said it is raised "when reading
what an object the walk reached holds raises". Reading a declared slot never assigned raises, and so does reading an
empty closure cell, yet the walk reads each as holding nothing, and the pair is admitted; only another error raised
while reading refuses it. Both docstrings now say so and name the tests that measure it. `378-63-a` is left as
written; this fragment corrects it.

**What measures it:**
`tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_control_a_slot_never_assigned_still_reads_as_holding_nothing`,
`tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_control_an_empty_closure_cell_still_reads_as_holding_nothing`
(whose twin, the same cell holding the subject-keyed phase's object, is refused) and
`tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_a_member_the_walk_cannot_read_is_refused_by_name`,
each at both places the guard runs. They pin the behavior as it stands, so they are green before and after the words
change.

## ccf.products.resolver.PopulationPhaseSharesAnOwner

- Surface: ccf.products.resolver.PopulationPhaseSharesAnOwner
- Public surface: true
- Change type: behavior
- Before: its docstring said that where reading what an object holds raises, the walk cannot complete and the two phases are refused (`SharedOwnerWalkIncomplete`).
- After: unchanged behavior; its docstring says that a declared slot never assigned and an empty closure cell hold nothing and are read so, and that where reading what an object holds raises otherwise the two phases are refused, naming the test that measures each.
- Why: `D-IMPL-378`, the "j" batch panel's J-SP-WALK-READS (a refusal advertised for two reads the walk admits). Measured by `tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_control_a_slot_never_assigned_still_reads_as_holding_nothing`, `tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_control_an_empty_closure_cell_still_reads_as_holding_nothing` and `tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_a_member_the_walk_cannot_read_is_refused_by_name`.
- Migration: none.

## ccf.products.resolver.SharedOwnerWalkIncomplete

- Surface: ccf.products.resolver.SharedOwnerWalkIncomplete
- Public surface: true
- Change type: behavior
- Before: its docstring named a declared slot never assigned, but not an empty closure cell, as read as holding nothing; fragment `378-63-a` said it is raised "when reading what an object the walk reached holds raises".
- After: unchanged behavior, stated as it is: it is raised where reading what an object the walk reached holds raises, except for a declared slot never assigned and an empty closure cell, which hold nothing and are read so; its docstring names both, and the tests that measure them.
- Why: `D-IMPL-378`, J-SP-WALK-READS. Measured as for `ccf.products.resolver.PopulationPhaseSharesAnOwner`.
- Migration: none.
