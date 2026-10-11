# 378-63-a (repair 1.8) — SEC-020 Q7: a member the shared-owner walk cannot read is refused by name

`D-IMPL-378` repair 1.8, ruled by Dave on 2026-10-09 at 10:54 MST: *"Implement the specified documentation,
citation-checker and shared-owner fixes."* As the "i" panel's findings brief specified it: *"Handle a foreign
member descriptor's `TypeError` as the walk handles an unread slot (or refuse, per 2.4); name MappingProxyType,
cell objects, generator frames and `methodcaller` among what the walk does not read."* Read with repair 2.4 (b),
ruled in the same text (*"Refuse when the shared-owner walk reaches a limit before completing."*): a member the
walk cannot read means the walk cannot complete. Lane `378j-q7`, on the panel's Fable G1 finding F-G1-5.
**SEC-020 stays OPEN.**

**What was measured before the change**, on `dl-378-integ` @ `fe25536c`: a population phase whose slotted class
namespace holds another class's member descriptor made `GovernedResolver` construction and `open_product` raise
a bare `TypeError` ("descriptor 'borrowed' for '_ForeignSlots' objects doesn't apply to a
'_PopulationWithAForeignDescriptor' object"), whether or not the phase held anything of the other phase.

**What holds now**, in `tests/products/test_q7_walk_unreadable_member_and_unread_holders.py` (12 tests; 4 failed
before the change, 8 passed before and after). At both places the guard runs, that phase is refused with
`SharedOwnerWalkIncomplete`, whose message names the phase walked from, the error's type (never its text), the
step and the references read. A declared slot never assigned still reads as holding nothing and is admitted.
Six holders are shown not read, each holding the subject-keyed phase's object and admitted, while the same
holding in a container the walk reads is refused: a `types.MappingProxyType`, a closure cell held in a list, a
generator's frame, an `operator.methodcaller`, a `functools.partial` and a `collections.deque`. Severing (the
`TypeError` skipped where the member is read) made the four refusal cases fail again; removing the conversion
in the walk brought the raw `TypeError` back. The two bounds still admit the pair when either is reached (as
`378-49` describes).

## ccf.products.resolver.SharedOwnerWalkIncomplete

- Surface: ccf.products.resolver.SharedOwnerWalkIncomplete
- Public surface: true
- Change type: added
- Before: absent; a member the shared-owner walk could not read raised its own error, such as a bare `TypeError`, out of construction and `open_product`.
- After: a `PopulationPhaseSharesAnOwner` raised where that refusal is (at `GovernedResolver` construction and at `open_product`) when reading what an object the walk reached holds raises. Its message names the phase the walk started from, the error's type, the step and the references read, and nothing any object holds.
- Why: `D-IMPL-378` repair 1.8. Red test: `tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_a_member_the_walk_cannot_read_is_refused_by_name`.
- Migration: none; additive. A handler for `PopulationPhaseSharesAnOwner` also catches it.

## ccf.products.resolver.PopulationPhaseSharesAnOwner

- Surface: ccf.products.resolver.PopulationPhaseSharesAnOwner
- Public surface: true
- Change type: behavior
- Before: its docstring named a `functools.partial`'s arguments and a `collections.deque`'s members as C-extension state the walk does not read; a member the walk could not read escaped as its own error.
- After: its docstring also names a `types.MappingProxyType`'s mapping, a generator's frame, an `operator.methodcaller`'s arguments and a closure cell held anywhere but in a function's closure, each measured, and states that a member the walk cannot read is refused by its subclass `SharedOwnerWalkIncomplete`.
- Why: `D-IMPL-378` repair 1.8.
- Migration: none.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: construction raised whatever error reading a member raised during the shared-owner walk, such as a bare `TypeError`.
- After: construction raises `SharedOwnerWalkIncomplete` in that case.
- Why: `D-IMPL-378` repair 1.8.
- Migration: as for `SharedOwnerWalkIncomplete`.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: open raised whatever error reading a member raised during the shared-owner walk over `population` and `acquire`.
- After: open raises `SharedOwnerWalkIncomplete` in that case; the `population` argument's description names it.
- Why: `D-IMPL-378` repair 1.8.
- Migration: as for `SharedOwnerWalkIncomplete`.
