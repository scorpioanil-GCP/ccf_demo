# 378-49 — SEC-020 Q7: the shared-owner guard walks what each phase holds, within two stated bounds

`D-IMPL-378`, decision 3 (a), ruled by Dave on 2026-10-09 (the 06:06 MST list, confirmed as "3a" at
06:21 MST): *"(a). Extend the shared-state guard, with a bounded walk and an explicit statement of what it
cannot detect."* Lane `378i-q7owner`, on the final panel's finding G-Q7-OWNER (the probe
`panel/probes/p_b01_q7_owner.py` on `dl-378-record`). **SEC-020 stays OPEN.**

**What the tests measure, on test fixtures.** In `tests/products/test_q7_shared_owner_bounded_walk.py`, at
both places the guard runs, a `GovernedResolver` built by hand and `open_product` on the paved road:

- **The hole.** Before the change, a population phase holding the subject-keyed phase's object as an
  attribute (the probe's shape A), or a closure holding a tuple that holds it (shape C), was admitted, and
  so were fifteen more ways of holding it (a slot; a list, set, frozenset, dict key, dict value, dict
  subclass, tuple subclass, `types.SimpleNamespace` or self-holding list in a closure; an attribute of a
  held object; positional and keyword-only default arguments; a function attribute; another bound method
  of the object in a container) and the subject-keyed phase's object holding the population phase. After,
  each raises `PopulationPhaseSharesAnOwner`. Each fixture is first shown to hold the object where its
  name says.
- **Controls.** Both phases bound to one object, a closure holding the subject-keyed phase itself, and a
  method whose function's closure holds the subject-keyed phase's object were refused before and after.
  Two phases sharing nothing were admitted before and after.
- **The limits, asserted as documented behavior.** An object one step past `SHARED_OWNER_WALK_DEPTH`, or
  reached only after `SHARED_OWNER_WALK_OBJECTS` references are read, is not seen, while the same holding
  inside each bound is refused. Not seen either: state shared through a third object (the probe's case B),
  a `functools.partial`'s arguments, a `collections.deque`'s members, a weak reference's referent, a class
  attribute and a class's own `__call__`, a module global, and the dictionary of a class that replaces
  `__dict__`. Hooks that raise when called (`__getattribute__`, `__getattr__`, a property, a `__class__`
  property, a metaclass's `__hash__`, `__eq__`, `__instancecheck__` and `__subclasscheck__`, and a list or
  dict subclass's own iteration and item methods) are never called, and the dictionary or members behind
  them are still read and refused.
- **Severing.** Putting back the one-level reading made shape A and shape C admitted again at both sites,
  with every other holding.

**What it costs, measured** by the lane on 2026-10-09, timing every call of the guard while `tests/products`
ran on `002bde8d` (the 173 calls made by tests that existed before this entry): at `open_product`, a
median of 14 µs and at most 37 µs; at `GovernedResolver` construction, a median of 1.4 ms and at most
4.8 ms. The walk runs where the guard always ran, and the paved road builds a resolver for every question,
so there it runs once per question. In the same suite before this entry, the guard took a median of 6 µs,
and a paved-road question with a declared population phase took a median of about 100 ms.

## ccf.products.resolver.PopulationPhaseSharesAnOwner

- Surface: ccf.products.resolver.PopulationPhaseSharesAnOwner
- Public surface: true
- Change type: behavior
- Before: raised when the two phases were one callable or were bound to one object, or when one phase's closure cells, read one level deep, held the other phase or the object it is bound to.
- After: also raised when either phase reaches the other phase, or the object the other is bound to, by a breadth-first walk of what it stores: the object a method is bound to and its function; a function's closure cells, default arguments and attributes; an object's declared slots and instance attributes; the members of a list, tuple, set or frozenset and the keys and values of a dict, subclasses included. The walk calls nothing an object defines and stops after `SHARED_OWNER_WALK_DEPTH` steps or `SHARED_OWNER_WALK_OBJECTS` references from a phase. Its docstring states what the walk cannot detect: anything past either bound; state shared through a third object; state reached only through a property, another descriptor, `__getattr__`, `__getattribute__` or a replaced `__dict__`; a C-extension object's own fields; module globals and class attributes; weak references and external stores.
- Why: SEC-020 Q7, decision 3 (a): the guard admitted a population phase holding the subject-keyed phase's object as an attribute, or in a container in a closure.
- Migration: declare the two phases on separate objects that hold nothing of each other. A composition where either phase holds the other's object through an attribute, a container, a default argument or a deeper closure is now refused at construction and at open.

## ccf.products.resolver.SHARED_OWNER_WALK_DEPTH

- Surface: ccf.products.resolver.SHARED_OWNER_WALK_DEPTH
- Public surface: true
- Change type: added
- Before: absent.
- After: `12`, the most steps the shared-owner walk follows from a phase. One step is one reference followed. An object more steps than this from each phase is not seen. Everything the phases the SDK's own tests compose hold was read within 10 steps.
- Why: SEC-020 Q7, decision 3 (a): the walk's depth bound, stated.
- Migration: none; additive.

## ccf.products.resolver.SHARED_OWNER_WALK_OBJECTS

- Surface: ccf.products.resolver.SHARED_OWNER_WALK_OBJECTS
- Public surface: true
- Change type: added
- Before: absent.
- After: `5000`, the most references the shared-owner walk reads from one phase, an object counted once for every reference to it that the walk reads, nearest first. What the walk would have reached after that is not seen. The most any phase the SDK's own tests compose holds is 3,989 references.
- Why: SEC-020 Q7, decision 3 (a): the walk's object bound, stated, which also caps its cost.
- Migration: none; additive.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: construction refused a population phase sharing an owner with the subject-keyed phase as `PopulationPhaseSharesAnOwner` described it before this entry.
- After: construction, and so `build_governed_resolver`, refuses with `PopulationPhaseSharesAnOwner` the compositions its walk finds; the walk runs at every construction, so on the paved road at every question with a declared population phase.
- Why: SEC-020 Q7, decision 3 (a).
- Migration: as for `PopulationPhaseSharesAnOwner`.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: refused at open a `population` sharing an owner with `acquire` as `PopulationPhaseSharesAnOwner` described it before this entry.
- After: refuses at open, with `PopulationPhaseSharesAnOwner`, a `population` and an `acquire` either of which the walk finds holding the other or the object it is bound to.
- Why: SEC-020 Q7, decision 3 (a).
- Migration: as for `PopulationPhaseSharesAnOwner`.
