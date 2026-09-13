"""D-IMPL-86 element (5) — Gate 2's two arguments may not share one source.

Two **tripwires** over the trees a gate call site and a projection can live in.
Tripwire is the accurate word and it is used deliberately throughout: these
catch known shapes, and D-IMPL-86 establishes that they cannot be made into
walls. Nothing here is on a par with the harness-import lint, which refuses a
category of *import* and has no evasion that stays inside the language.

The shape CR-2 found
--------------------

:func:`ccf.products.gates.run_gates` compares the product's declared
``lineage.operators_invoked`` against the engine's ``engine_resolved``. That
comparison is a check only while the two values arrive from two sources. At all
nine gate call sites in ``examples/`` before Phase 15.1, both sides read the
*same object*::

    lineage=ProductLineage(operators_invoked=execution.operators_invoked, ...)
    ...
    run_gates(candidate, engine_resolved=execution.operators_invoked, ...)

Gate 2 then compared a value against itself. It stayed green, it could not
fail, and whitepaper §7.6 / INV-CH7-47 was gone with nothing failing to say so.
Plans 15.1-05 through 15.1-07 repaired all nine instances. **That closes the
instances; this module closes the shape.** The next call site someone writes
has to be refused, not reviewed.

Why AST identifiers and not source text
----------------------------------------

Matched on ``ast`` nodes, exactly as ``test_required_operators_guard.py`` and
``test_gate_independence.py`` are, and for the same reason: a source-text grep
is fooled by a comment or a docstring that merely *mentions* the pattern —
including this module's own docstring three paragraphs above, which spells the
banned shape out in full so a reader can see it. A grep-based version of this
check would fail on its own explanation of itself.

What tripwire (1) catches
--------------------------

Within **one lexical body**: a ``run_gates`` call whose ``engine_resolved``
argument roots at some identifier path, paired with a ``ProductLineage``
construction whose ``operators_invoked`` argument roots at the *same* path (or
at a prefix of it). Paths, not bare roots — ``self._declared`` and
``self._resolved`` share a root and are two different values, and a check that
collapsed them to ``self`` would be red on correct code.

Local aliases are followed through assignment, annotated assignment and the
walrus, so ``resolved = execution.operators_invoked`` used on both sides is
caught rather than evaded by one statement. Set conversions (``frozenset``,
``tuple``, ``sorted``, and ``typing.cast``) are transparent, so wrapping one
side does not hide it.

**Following is position-aware, and that is a correctness property rather than a
refinement.** A name is resolved to the binding in force *at the position that
reads it* — ``(line, column)``, not a line — so a body that reuses an ordinary
local name for two different values has two sources and not one. Its first
predecessor kept one binding per name and was **red on correct code** for that
reason (WR-F2). The same model is what lets a binding this module cannot read
through still be a *source*: ``plan = QuickstartPlan(...)`` ending at line 231
column 84 is the token ``plan@231:84`` (:func:`_opaque`), so two reads of one
construction share a source and two constructions do not — which is object
identity, and is what property (2) below needs.

**Every binding form Python has is read, and the ones it cannot read through are
recorded as unreadable rather than skipped** (:func:`_binding_records`). That
distinction is CR-01, and it is not a refinement either: a *skipped* binding
leaves the previous one in force, so the checks go on describing an object the
name no longer holds — and answer **affirmatively**. A tuple unpack, a ``for``
target, a ``with … as``, an ``except … as``, an augmented assignment, a ``match``
capture, an import and a nested ``def``/``class`` each bound nothing under the
first predecessor, and each of them is a legal spelling of "this name is
something else now".

**Reading every form is not enough on its own, and the second predecessor is
the proof** (R4-CR-01). It recorded all of them and then consumed them with a
strictly-below *line* comparison, so a compound statement's suite written on its
own header line — ``for plan in alts: run(plan=plan)`` — read the name at a line
its own binding was not yet "before", and the **previous** binding answered.
Nine of the eleven spellings that round certified as rejected were admitted in
that spelling, silently, with every assertion in the module green. The consumer
is therefore position-ordered too, and each binding is anchored where it
actually takes effect: past its value expression, past a ``for``'s iterable,
past a ``with`` item's context expression (:func:`_binding_records`). A
comprehension's target binds as well, scoped to the comprehension's own
**lexical span** — its ``(line, column)`` extent, not its line range — because
in Python 3 it does not leak and because a line range over-covers every
expression sharing its first or last line (R4-WR-01).

**How this module names its findings.** ``CR-``/``WR-``/``IN-`` tags without a
prefix belong to the review round that raised them, and the rounds reuse
numbers; tags prefixed ``R4-`` are the fourth review's
(``15.1-REVIEW-FIXES-3.md``), which would otherwise collide with the first
review's ``WR-F5``/``WR-F6`` and with ``IN-F1``.

What tripwire (1) cannot catch — the structural limit, not a caution
---------------------------------------------------------------------

**This list is the known set, not a proof of completeness.** Four review rounds
have each added to it, every time by finding a shape the module was silent on
while its own docstring read as an enumeration. Read it as "these are the ones
that have been found", and note that two entries below (the loop-carried
rebinding, the two positional approximations) were added only after they were
measured — the phrasing before was a closed list that did not name them.

* A value arriving through **a helper's return value**. ``derive(execution)``
  roots at the helper, and this module deliberately stops there rather than
  guessing what the helper returns.
* A value arriving through **two different methods that happen to return the
  same object**. A method call resolves to its receiver's path extended by the
  method name and a call marker — ``execution.resolved()`` is
  ``("execution", "resolved", "()")`` — so ``a.keys()`` and ``a.key_set()`` are
  two paths and are two sources, whatever they return. What that spelling
  *does* read is the member, which is the whole of WR-F4: the identical call on
  both sides of Gate 2 is one path and is caught, while
  ``self.declared_claim()`` and ``self._resolved`` differ in their **second**
  element and are two, so a correct body stays quiet. Collapsing a call to its
  bare *receiver* — the shape WR-02 removed — is what was red on correct code,
  because it made *any* method call on an object share a source with *any*
  attribute read of it. Keeping the member name is what lets the true positive
  back in without the false one; dropping the call entirely, which is what the
  WR-02 fix did, admitted ``execution.resolved()`` on both sides.
* A value arriving through **a container** — ``results["ops"]`` — or through
  **dynamic attribute access** — ``getattr(execution, "operators_" + "invoked")``.
  Neither has an identifier path an AST walk can read.
* A value carried across a **body boundary** by an attribute set in one method
  and read in another.
* **A write to an attribute or a subscript is not followed.** ``self._ops = …``
  and ``d["ops"] = …`` bind a *member*, not a local name, and this module's
  binding map is keyed by local name. The consequence is bounded and worth
  stating precisely: because nothing was ever bound to ``self._ops`` here, a read
  of it resolves to the literal path ``("self", "_ops")`` rather than to a stale
  value — the write is unfollowed, never misfollowed. ``global`` and ``nonlocal``
  are likewise not modelled: they redirect where an assignment lands, they do not
  bind, and the assignment itself is still recorded.
* **An augmented assignment is an *unreadable* binding, and that costs one true
  positive.** ``ops |= execution.operators_invoked`` binds a value derived from
  both sides and equal to neither, so it is recorded as opaque. That is what
  stops the false positive CR-01 measured — reporting the post-``|=`` value as
  still reading the pre-``|=`` path, which is a message that is simply untrue.
  Where ``ops`` is a **mutable** set, ``|=`` mutates in place and the object the
  lineage already holds changes with it; that body is admitted, and no AST walk
  can tell the mutable case from the rebinding one.
* **A rebinding that executes before it is written — a loop-carried one — is
  invisible** (R4-WR-03). The binding model answers "which binding is textually
  last before this position", which is the right answer only for straight-line
  code. In::

      ops = frozenset(declared.required_operator_keys)
      product = ProductLineage(operators_invoked=ops)
      for item in batches:
          out = run_gates(candidate, engine_resolved=ops)
          ops = recompute(item)

  the ``ops`` the gate reads on the second and every later iteration is line
  5's, and this module reads line 5's binding as never in force at line 4. The
  binder-side spelling of the same shape — a plan rebuilt at the bottom of a
  loop whose ``execute`` is at the top — is admitted for the same reason and is
  measured in :func:`test_a_loop_carried_rebinding_is_out_of_reach_and_says_so`.
  Closing it needs **control-flow** ordering, not lexical ordering, which is a
  different kind of analysis from the one this module is; it is named here
  rather than implied away, and it is not a residual the position model
  introduced — it is the property a one-pass textual walk has.
* **Source order is taken for evaluation order, and twice it is not.** Ordering
  ``(line, column)`` is exact for the statements and the top-level argument
  expressions this module compares. It is *not* exact inside a comprehension,
  whose outermost iterable is evaluated before the element expression written to
  its left, nor for a ``lambda``, whose body runs when it is called rather than
  where it sits. Neither has produced a wrong verdict on any body measured, and
  neither is modelled.
* And the limit that makes all of the above secondary: **D-IMPL-86 established
  that no AST gate can distinguish an authored literal from a transcribed
  one.** An author who types the engine's operator set out by hand into the
  lineage produces source that is textually identical to an author who derived
  it. That finding is why the D-GATE-15 second amendment *strengthened* the
  tripwire framing from an advisory to a structural limit.

The claim this module supports is therefore "the shape CR-2 found at nine
sites, and the obvious evasions of it" — never "impossible to write".

What tripwire (2) catches, and what it can only assert
-------------------------------------------------------

Tripwire (2) is **two checks, deliberately kept apart**, because collapsing
them is what CR-03 found.

**Coverage, conditioned on its own premise.** Every lexical body under
``examples/`` that constructs a projection plan, or runs one through
``ProjectionEngine(...).execute(...)``, must **name**
:func:`ccf.deployment.refuse_operator_set_divergence` — *where the deployment
that body sits in has two independently authored operator-set documents for
the binder to compare*.
The qualifier is D-IMPL-137 (2026-08-14), which narrows D-IMPL-86 without
revoking it, and it is here because without it the demand had **no compliant
state** for a one-document deployment: the coverage assertion demanded the
call, and had that deployment made it, property (1) below would have refused
the same call as a tautology. The only exit property (1)'s own message names —
*"build the plan's ``required=`` from the projection's OWN document"* — is not
a code edit but the authoring of a second artifact. So the demand was not
*call the binder*; it was *adopt the two-document design*, which is a design
mandate wearing a call-site check's clothing.

**The premise is a fact about the Control Plane, and is read there.** A
deployment has a second operator-set document when its artifact tree
**registers** one: any manifest under it declaring ``class_id:
ccf.projection-requirements`` (:data:`REQUIREMENTS_CLASS_ID`). *Any* manifest,
because the filename varies — ``archive/examples/04-cross-process`` declares it in
``producer-manifest.yaml``, so a fixed filename would answer wrongly there. A
deployment that authors **one** document has no second operand for the binder
to compare, and there is nothing for the call to do.

**The detector is a conjunction of two independent readings, and every other
combination is refused** (:func:`_one_document`). The artifact tree says
whether a second document is registered; the AST says whether the code in fact
reads one source for both sides.

* Registration **absent** AND the plan's ``required=`` **sharing** a source
  with the product class's claim ⇒ one document, and the demand does not fire.
* Registration **present** AND sharing ⇒ refused by property (1), unchanged.
* Registration **absent** AND **not** sharing ⇒ **refused**. A second operator
  set was authored somewhere the Control Plane does not know about, and the two
  readings disagreeing is itself the finding. This is the row the exemption
  must never admit, and it stays red because :func:`_one_document` returns
  ``False`` for it.

**Fail-closed in three places** — no artifact tree, no readable class claim, no
readable plan source — each of which means the demand applies. An absence of
evidence is not the exemption; the exemption is claimable only by a deployment
that HAS artifacts and demonstrably lacks that one registration.

**The first guard's control is
:func:`test_a_body_with_no_artifact_tree_is_subject_to_the_demand`, and naming
it correctly matters because this paragraph has now been wrong twice.** That
test's synthesized body *does* assemble a ``ProductLineage``, and its plan's
lone ``required=`` resolves to the identical path — the AST agreement that
would otherwise grant the exemption — so it reaches the artifact-tree guard and
is refused *by that guard* rather than by anything downstream of it. The hazard
the guard closes is an adopter tree **outside** ``examples/`` that assembles a
lineage and reads one source: without it, such a tree would buy the exemption
by having no Control Plane at all, which is the inverse of what the exemption
is earned by.

**Two controls the first guard is not *needed* for, both of which earlier
revisions of this paragraph claimed it protected.** They are recorded as
retracted rather than deleted, on the same discipline the two lists above keep:
the reader who most needs this paragraph is the one checking whether it is still
true. (a) :func:`test_the_binder_argument_checks_reject_a_binder_that_cannot_fail`
synthesizes its bodies against ``REPO_ROOT / "probe.py"``. **Both fail-closed
guards are independently sufficient for those bodies**: ``probe.py`` is outside
``examples/``, so :func:`_deployment_root` answers ``None``, and **none of them
assembles a lineage**, so :func:`_class_claim` answers ``None`` too. **The first
guard is the one that executes** — the two are spelled ``root is None or
_registers_requirements(root)``, so the ``or`` short-circuits and the class
claim is never read for these bodies at all. That redundancy is precisely why
removing the first guard alone changes **not one** of their verdicts, measured
body by body — the fact that retired the original attribution. And under the
strongest reading of a default of *exempt* the tautology body still reports,
because property (1) is unconditional, so that control would have gone **red**
rather than silently green. (b)
:func:`test_the_binder_tripwire_detects_a_projection_that_skips_it` calls
:func:`_names_the_binder`, :func:`_is_plan_construction` and
:func:`_is_plan_execution`, passes **no path at all**, and never reaches
:func:`_one_document` — the conditioning cannot silence it in either direction.
The policy is unchanged by either retraction; only the argument for it was
wrong.

**Arguments.** Naming it is not enough, and for one wave it was all that was
asked. A body can name the binder and route around it completely::

    plan = FooPlan(plan_id='p', required=declared.required_operator_keys)
    refuse_operator_set_divergence(declared=declared, plan=plan)
    return ProjectionEngine(reader=r).execute(plan=plan)

``plan.required_operators()`` is now ``declared.required_operator_keys``, so
``claimed == required`` holds unconditionally at
``refuse_operator_set_divergence``'s comparison. The
binder is green, it *cannot* fail, and the ``ccf.projection-requirements``
artifact has been routed around entirely — CR-2's shape moved one seam
upstream. So the call's arguments are read as well as its name, for three
properties (:func:`_binder_collapses`):

1. the plan handed to the binder does not read its ``required=`` from the same
   source as the binder's ``declared=``;
2. the plan handed to the binder is the plan the engine runs — which also
   requires the **hoist**, since a plan constructed inline as ``execute``'s own
   ``plan=`` argument is not an object any binder could have been handed; and
3. the binder call precedes the engine call, per D-IMPL-86's correction.

**Properties (2) and (3) are conditioned on the premise above; property (1) is
not.** (2) and (3) ask whether the binder was called on the right object at the
right time, and where the deployment authors one document there is no call for
them to ask about — property (2), spelled ``any(… for call in calls)``, would
otherwise fire on **every** execution merely because ``calls`` is empty, which
is red on a deployment D-IMPL-137 declares correct. Property (1) stays
unconditional, and that is precisely what makes this an **absence of demand**
rather than a **licence**: a one-document body that calls the binder anyway is
still refused for the tautology, so the exemption buys nobody the collapsed
shape.

Two things the conditioning does **not** touch, since both are easy to assume
it does. Gate 2 proper is unmoved — the L6 comparison of
``lineage.operators_invoked`` against ``engine_resolved`` still does real work
in a one-document deployment, because those two sides are the *declaration* and
the *engine's resolution*, which are two sources whatever the upstream document
count is. And tripwire (1) is not conditioned at all.

``refuse_operator_set_divergence`` returns ``None`` by contract — deliberately,
so it can never grow into a helper that supplies one of Gate 2's arguments. The
consequence is that **nothing observable at runtime proves the call happened**:
no product field, no pin, no audit event. A deployment that omits it produces
output byte-identical to one that made it. An AST check is therefore the only
mechanism available, and this module claims exactly that and no more.

What tripwire (2) still cannot see
-----------------------------------

Named rather than implied away, and each one distinct from the authorship
residual below. **This list is the known set and not a completeness claim** —
same discipline as tripwire (1)'s above, and for the same reason: every round of
this phase has found one more, and the reader who most needs this section is the
one looking for what is missing from it.

* **Reachability.** A binder call inside a never-taken ``if``, an ``except``
  handler or a ``# pragma: no cover`` branch is named, is ordered before the
  engine, and never runs. Ordering is readable from source positions and is
  checked; reachability is not readable from an AST walk and is not.
* **A loop-carried rebinding** (R4-WR-03), which is tripwire (1)'s entry of the
  same name at this seam: a plan rebuilt at the *bottom* of a loop body whose
  ``execute`` is at the top runs, from the second iteration on, a plan no binder
  was handed — and the ordering here is textual, so the rebinding reads as never
  in force. Measured and left open in
  :func:`test_a_loop_carried_rebinding_is_out_of_reach_and_says_so`; it needs
  control-flow ordering, which this module does not have.
* **A plan expression with no identifier path.** ``execute(plan=build(spec))``
  roots at a helper, so property (2) cannot say which plan ran — the same limit
  tripwire (1) has, in the same place.
* **A ``required=`` expression with no identifier path.** Property (1) compares
  two resolved paths, so ``required=[*claim]``, ``required=claim[:]``,
  ``required=derive(claim)`` and ``required=claim.as_keys()`` each resolve to
  ``None`` and the property reports nothing. This is property (1)'s *only*
  input, so it is the residual that matters most for it, and it was previously
  unstated. ``MINIMUM_RESOLVED_BINDER_SITES`` holds the *existing* sites
  readable and does not stop a new one arriving unreadable — which is why
  :func:`test_every_bound_body_has_a_readable_plan_source` asserts the property
  **per binder call**, where a count cannot. Per call and not per body: an
  ``any()`` over the body's calls composes the same arithmetic one level down,
  and one compliant readable site then licenses any number of unreadable ones
  beside it (WR-02). A plan bound by a tuple element —
  ``plan, spare = FooPlan(…), None`` — lands here too: the *binding* is recorded
  (CR-01), so property (2) sees the rebinding, while the plan's ``required=``
  is not readable through the tuple and that call is reported unreadable.
* **``engine.execute(**kwargs)``.** :func:`_is_plan_execution` needs a keyword
  literally named ``plan``; ``**`` gives ``keyword.arg is None``, so a body that
  only executes — constructing no plan — is not a projecting body under that
  spelling.
* **A plan crossing a body boundary.** A plan constructed and bound in one
  method and executed in another is two bodies, and one body means one body.
* **A plan class this module can neither see nor recognise.** Plan
  *construction* is recognised three ways, and the two that carry the check are
  **name-independent**: the callee names a class defined in the scanned trees
  whose body defines both ``required_operators()`` and ``invoke()`` — which is
  ``ProjectionPlan``'s own structural test, taken verbatim from its docstring
  — or the call passes both ``plan_id=`` and ``required=``, the constructor
  shape every plan in the suite has and the two keywords the check actually
  reads. The ``*Plan`` class-name suffix survives only as a third net; see
  :func:`_is_plan_construction` for why it is kept and why it is no longer what
  the check rests on. What genuinely survives is a plan class defined
  **outside** ``src/``, ``runtime/`` and ``examples/``, constructed without
  either conventional keyword and not named ``*Plan``; and a plan produced by a
  factory, where there is no class name at the call site at all. Plan
  *execution* is separately robust: ``ProjectionEngine.execute`` declares
  ``plan`` keyword-only, so any body that runs a projection through the SDK's
  engine passes ``plan=`` whatever its plan class is called.
* **A body under a tree this module does not scan.** ``BINDER_SCANNED_TREES``
  is ``examples/`` alone, which the scope note below states as the honest
  bound; and nothing holds an adopter's deployment to calling the binder at all
  (D-IMPL-86 correction, 2026-08-05 — Phase 16's).
* **A deployment leaving the demand by collapsing into one document.** The
  D-IMPL-137 conditioning is read from the tree at test time, so a deployment
  that deletes its ``ccf.projection-requirements`` registration and repoints its
  plan's ``required=`` at the product class's own claim stops being demanded of,
  and this module reports nothing — it has become the shape the ruling declares
  correct. What bounds that is **a roster, not a structure**:
  :data:`RULED_ONE_DOCUMENT_DEPLOYMENTS` names its claimants, so a deployment
  nobody ruled onto it is red at
  :func:`test_the_one_document_exemption_has_not_spread`, and a ruled one is
  visible in a diff, where the deleted artifact and the changed ``required=``
  are both on the page. **Visible and bounded is not prevented**, and the
  distinction is the one the floors already carry: nothing at the failure site
  tells a deliberate collapse from an accidental one, only ``git log`` does.

Two shapes that WERE on this list and are not any more, so a reader comparing
revisions can see which way each moved:

* **A compound statement's suite on its own header line, and a rebinding
  separated by a semicolon.** These were never *on* the list — they were
  admitted while the module certified them closed (R4-CR-01). Both are now
  rejected, measured in
  :func:`test_a_rebinding_on_the_statements_own_line_is_seen`, and the reason
  they are recorded here rather than dropped in silence is that the round before
  this one asserted their closure without measuring the one-line form.
* **A walrus around an inline plan construction** (R4-WR-02), which routed past
  property (2)'s hoist branch. Now unwrapped; measured in
  :func:`test_a_walrus_does_not_route_around_the_hoist_branch`.

The authorship residual is **not** closed by any of this
---------------------------------------------------------

The argument checks read *code*, and the two must not be conflated. A plan
built as ``required=declared.required_operator_keys`` is a readable identifier
path in a source file, which is why it is detectable and is now detected. The
**authorship** residual — an author copying one YAML document's operator keys
into the other, so that the two artifacts agree because they were transcribed
rather than because they were independently authored — is a different thing at
a different boundary, and D-IMPL-86 establishes it as undetectable **in
principle**: the compliant artifact and the violating artifact are textually
identical, so there is nothing for any gate to read.

It remains open, and it is Phase 16's, exactly as
``src/ccf/deployment/binder.py``'s module docstring records it. Nothing in this
module narrows it, and a reader who takes "the binder tripwire was
strengthened" for "dual authorship is now enforced" has taken the wrong
conclusion.

Granularity is the **lexical body, not the file**. ``archive/examples/06-decision-replay/run.py``
and ``archive/examples/external/00-hello-context/run.py`` each carry two plan-construction
sites, and a file-level check would let one of the two go unbound while the file
still passed.

Two shapes are admitted as projecting, and both are needed. A body that
constructs a plan and executes it is the common case. A body that constructs a
plan and **returns** it without executing — the ``resolve_plan`` methods of the
two replay environments — is equally a plan-construction site, and the engine
call for it happens inside ``ccf.replay.engine.replay``. A check that required
the binder and the ``execute`` call to appear together would be **red on two
correct sites**; that is why "constructs a plan" is a sufficient trigger on its
own.

Scope, stated rather than implied: this tripwire is on ``examples/`` — the
SDK's own teaching material. **Nothing holds an adopter's deployment to calling
the binder at all.** That residual is D-IMPL-86 (correction, 2026-08-05)'s, it
is recorded in ``src/ccf/deployment/binder.py``'s module docstring, and it is
carried to Phase 16 rather than closed here.

Why ``tests/`` is excluded from both scans
-------------------------------------------

``SCANNED_TREES`` omits ``tests``, copying
``tests/products/test_required_operators_guard.py::SCANNED_TREES`` and its
stated reason: a test may legitimately build a deliberately-tautological
construction in order to prove that a guard fires.
``tests/examples/test_gate_two_divergence.py`` — this plan's third module — is
one of the places that happens, and ``tests/products/test_gate_independence.py``
is another.
"""

from __future__ import annotations

import ast
import contextlib
import pathlib
import re
import signal
import types
from collections.abc import Iterator
from typing import NamedTuple

import pytest
import yaml

#: The binding document's own vocabulary, imported from the SDK rather than
#: respelled here. This gate has to read the **same** key
#: :func:`~ccf.client.adapters.inprocess._boot` reads, and two spellings of one
#: vocabulary drift silently — the defect class this module already guards
#: against with :func:`test_this_module_gates_the_same_set_the_tool_checks`.
#: :func:`test_the_binding_documents_reference_surface_is_still_one_key` refuses
#: to let the import go stale.
from ccf.client.adapters.binding_document import (
    BINDING_DOCUMENT_NAME,
    REFERENCE_KEYS,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The trees a gate call site can live in. ``tests/`` is deliberately excluded
#: — see the docstring's closing section.
#:
#: ``archive`` joined in plan ``23-03``, ahead of Phase 23's move of ten
#: condemned example trees into ``archive/examples/`` (``D-03``). Measured on
#: the pre-move tree, 9 of the 12 gate call sites and 11 of the 14 projecting
#: bodies live in those ten trees, so without the member all three floors below
#: go red after the move — at 3, 3 and 1 — in a way that reads like a
#: legitimate removal. **The roots were widened and no floor was touched.** The
#: same witnesses are found at the new path, so every count is preserved
#: exactly; lowering a floor instead is the fix that sheds the coverage, which
#: is the trade :func:`test_the_binder_scan_is_not_vacuous` refuses in its own
#: docstring.
#:
#: The member is the top-level ``archive``, matching this tuple's existing
#: shape (tree names joined to ``REPO_ROOT``, not path prefixes) and
#: ``tools/lints/__main__.py::LINTED_TREES``'s spelling — deliberately not the
#: narrow ``archive/examples/`` the default-deny publication allowlist took in
#: plan ``23-02``. Guarded by
#: :func:`test_the_scan_root_membership_is_exactly_the_expected_sets`, because
#: none of the three floors can see one root swapped for another.
SCANNED_TREES: tuple[str, ...] = ("src", "runtime", "examples", "archive")

#: The trees the binder-coverage tripwire scans. Example trees only, and the
#: docstring says why that is the honest scope rather than a shortfall — the
#: archive is example trees that were retired, not a new kind of subject.
BINDER_SCANNED_TREES: tuple[str, ...] = ("examples", "archive")

#: The gate call and the keyword carrying the engine's side of Gate 2.
GATE_CALL = "run_gates"
GATE_RESOLVED_KEYWORD = "engine_resolved"

#: The lineage construction and the keyword carrying the product's side.
LINEAGE_CONSTRUCTOR = "ProductLineage"
LINEAGE_DECLARED_KEYWORD = "operators_invoked"

#: The binder every projecting body must name (D-IMPL-86 element (3), as
#: corrected 2026-08-05).
#: How a body says "the SDK owns my plan-construction -> execution seam".
#:
#: `D-IMPL-300`. Named structurally rather than by example, so the scope rule
#: below stays durable for every canonical adopter after cp-05.
CANONICAL_RESOLVER_ENTRYPOINTS: frozenset[str] = frozenset(
    {"build_governed_resolver", "GovernedResolver"}
)

BINDER_CALL = "refuse_operator_set_divergence"

#: The binder's two keyword arguments. ``declared=`` carries the Control Plane
#: **claim**; ``plan=`` carries the plan whose ``required_operators()`` is
#: compared against it. Naming the binder is not enough — these two are what
#: has to arrive from two documents, and checking that is what turns tripwire
#: (2) from a spelling check into a check.
BINDER_DECLARED_KEYWORD = "declared"
BINDER_PLAN_KEYWORD = "plan"

#: The Control Plane class the binder's second operand comes from. Its
#: registration is the premise the binder demand rests on: design E2 compares
#: the product class's claim against the projection's OWN document, and a
#: deployment that authors one document has no second operand for the
#: comparison. Read from any manifest in the deployment's artifact tree —
#: `archive/examples/04-cross-process` declares it in `producer-manifest.yaml`, so a
#: fixed filename would answer wrongly there (D-IMPL-137).
REQUIREMENTS_CLASS_ID = "ccf.projection-requirements"

#: How that registration is spelled in a manifest. The `class_id:` line is the
#: Control Plane registration proper; the artifact file's own `$schema` comment
#: names the same string and is deliberately NOT the signal, because a file
#: present but unregistered is not in force.
REQUIREMENTS_REGISTRATION_RE = re.compile(
    rf"^[ \t]*class_id:[ \t]*{re.escape(REQUIREMENTS_CLASS_ID)}[ \t]*$", re.MULTILINE
)

#: The `D-IMPL-136` single-file config section the product class is authored in,
#: and the attribute that section's operator set is spelled with. Both are
#: someone else's names — the first is a key of
#: ``ccf.deployment.config``'s reserved-section table, the second a field of
#: :class:`~ccf.controlplane.artifacts.ProductClassDeclaration` — so both are
#: asserted against the SDK by
#: :func:`test_the_product_class_surface_still_names_its_operator_set`
#: rather than believed. A rename there must turn that red, not make
#: :func:`_supplied_by_the_product_class` match nothing and quietly hand out no
#: exemptions, which would look like the gate tightening (`D-IMPL-234`).
PRODUCT_CLASS_SECTION = "product_class"
PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE = "required_operator_keys"

#: Deployments ruled onto the one-document exemption, **by name and not by
#: count**. The module's floors stop coverage shrinking silently and this stops
#: the exemption spreading silently, which is the same instrument inverted.
#:
#: **A roster, because a count cannot see a swap.** This was
#: ``MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1`` until 2026-08-27, when ``cp-00``
#: arrived as a second claimant and Dave ruled it onto the exemption rather than
#: onto a raised ceiling: *"Raise the ceiling to 2 with a named roster — not a
#: bare count ... next claimant is silent if someone deletes a name from the
#: list and the count stays 2."* A cardinality of two is satisfied by ANY two
#: deployments, so a ruled member leaving while an unruled one arrives keeps the
#: number right and the membership wrong — the shape that audits clean forever.
#: Set equality is red on arrival AND on departure, and the departure half is
#: not a nuisance: it means the ruled record has stopped describing the tree.
#:
#: **``cp-00`` is on it because it is the same collapse the exemption was
#: written for** — it authors ONE operator-set document where two were
#: possible, takes the identical route ``s1-00`` takes, and needed no new
#: detector to be seen. That last part is what separates this from `D-IMPL-146`,
#: where a raise was REFUSED because the detector was wrong and the fix was to
#: teach it; here the detector is right and names both claimants itself.
#:
#: A THIRD claimant is red until a human rules on it, which is what *"no
#: headroom"* meant all along: every new name gets a look, not that the number
#: can never change.
#:
#: **``cp-04`` is the third, and it is here because `D-IMPL-234` ruled it here
#: — in the entry, before the edit, which is what the sentence above exists to
#: force.** It is a different SHAPE of one-document deployment from the two
#: above, and that difference is why the detector had to be taught rather than
#: the list appended to: ``cp-00`` and ``s1-00`` author one document and read it
#: twice *in the same body*, so :func:`_class_claim` and :func:`_plan_sources`
#: both see it. ``cp-04`` assembles its lineage in a sibling function, so the
#: in-body claim is absent — and an absent claim is not evidence of anything,
#: which is why :func:`_one_document`'s fail-closed default refused it. What
#: earns the exemption is the POSITIVE reading `D-IMPL-234` names:
#: :func:`_supplied_by_the_product_class`. Dave: *"The binder's premise is two
#: documents that can disagree. cp-04 has one authored side; ``required`` would
#: be compared to itself. That is the tautology you already refused after
#: 17-13."*
#:
#: **The six below are the whole roster.** ``cp-01``, ``cp-02`` and ``cp-03``
#: arrived in Phases 24.2, 24.2.1 and 24.3 claiming this exemption with no
#: ruling, and `D-IMPL-234` expressly did NOT rule them in: *"Dave raised the
#: ceiling by ONE, for cp-04 ... each of the three needs its own sitting."*
#: That sitting was the Phase 24.5 discuss sitting, ledger row ``24.5-L-45``,
#: and `D-IMPL-239` is the ruling — Dave: *"Rule all three in, by name."* —
#: written in the entry before this edit, which is exactly what "red until a
#: human rules on it" above exists to force. All three arrived by the identical
#: route ``cp-00`` (`D-66`) and ``cp-04`` (`D-IMPL-234`) took: one authored
#: operator-set document, ``required=`` read from the product class's own
#: claim, no ``ccf.projection-requirements`` registration — the shape
#: `D-IMPL-137` names as legitimate. The carve `D-IMPL-234` cut into
#: `D-GATE-24.4`'s suite-green sentence is discharged with `D-IMPL-239`: from
#: Phase 24.5 on, a suite-green claim may not exclude
#: :func:`test_the_one_document_exemption_has_not_spread` by number.
RULED_ONE_DOCUMENT_DEPLOYMENTS: frozenset[str] = frozenset(
    {
        "examples/cp-00-institutional-holders",
        # `examples/s1-00-companies-over-revenue` was HERE and was REMOVED on
        # 2026-09-09 at its canonical adoption (`D-IMPL-311`), on the cp-05
        # precedent below. The reason is architectural, not administrative:
        # s1-00's hand-composed producer built its plan with
        # `required=tuple(scenario.product_class.required_operator_keys)` — one
        # document where two were possible, which is exactly what the exemption
        # permitted — and its `plan_factory` now consumes the resolver's
        # `required` and authors no operator set at all. Dave: *"s1-00 no longer
        # authors an operator set; the SDK supplies it."* It moved to
        # `RULED_SDK_SUPPLIED_DEPLOYMENTS` in the same commit, and no new
        # exemption class was created and no ceiling raised.
        # D-IMPL-234 (Dave, 2026-09-01) — the gate-two closure for cp-04.
        "examples/cp-04-corporate-family-tree",
        # D-IMPL-239 (Dave, 2026-09-02) — ruled in by name on ledger row 24.5-L-45.
        "examples/cp-01-counterparty-reference-snapshot",
        # D-IMPL-239 (Dave, 2026-09-02) — ruled in by name on ledger row 24.5-L-45.
        "examples/cp-02-facility-terms-snapshot",
        # D-IMPL-239 (Dave, 2026-09-02) — ruled in by name on ledger row 24.5-L-45.
        "examples/cp-03-obligor-financial-spread",
        # `examples/cp-05-credit-exposure-rollup` was HERE and was REMOVED at
        # cp-05's canonical adoption (`D-IMPL-298`, `D-IMPL-300`). It was ruled
        # in on 2026-09-08 as a one-document deployment; the migration deleted
        # the hand-composed spine whose `plan_factory` authored the second
        # operator-set site the exemption existed to permit. Dave: *"cp-05 no
        # longer authors the second operator-set site that required the
        # exemption ... do not replace it with a different exemption."* The
        # roster count goes DOWN, which is the whole point of the migration.
    }
)

#: Deployments claiming the `D-IMPL-141` **SDK-supplied** exemption — the
#: deployment authors no operator set at all, because
#: :func:`~ccf.products.resolver.build_governed_resolver` hands its projection
#: factory one derived from the registered product class.
#:
#: **A separate roster from** :data:`RULED_ONE_DOCUMENT_DEPLOYMENTS`, and the
#: separation is the point rather than bookkeeping. The two exemptions are
#: different claims — *one document where two were possible* versus *no document
#: at all* — and one shared population would let either grow into the other's
#: room while both read green. Named here for the same reason and judged by the
#: same predicate: an unruled claimant is red, and a human rules on it.
RULED_SDK_SUPPLIED_DEPLOYMENTS: frozenset[str] = frozenset(
    {
        "examples/hw1-companies-over-revenue/deployment",
        # `D-IMPL-301` — and it is EVIDENCE THE MIGRATION SUCCEEDED, not
        # bookkeeping. cp-05 changed architectural category: it authored its own
        # operator set and needed `D-IMPL-137`'s exemption — *one document where
        # two were possible* — and now authors none, because the SDK supplies
        # the canonical set. Dave: *"a classification update, not an exemption
        # swap."*
        #
        # It qualifies under shape B of `_resolver_owns_the_seam` because the
        # tree proves it, not because it is listed: no
        # `ccf.projection-requirements`; `plan_factory` consumes the resolver's
        # `required` and authors nothing; no competing operator set; no
        # projection engine of its own.
        "examples/cp-05-credit-exposure-rollup",
        # `D-IMPL-311` (Dave, 2026-09-09) — s1-00's canonical adoption, and the
        # same move for the same reason. Removed from
        # `RULED_ONE_DOCUMENT_DEPLOYMENTS` in this commit rather than held in
        # both: *"a classification update, not an exemption swap."* It
        # qualifies because the tree proves it — no
        # `ccf.projection-requirements`, a `plan_factory` that authors nothing,
        # no competing operator set, no projection engine of its own — not
        # because it is named here.
        "examples/s1-00-companies-over-revenue",
        # `D-IMPL-315` / `D-IMPL-313` tightening 1 (Dave, 2026-09-10) — the
        # canonical rung-4 successor, and the FIRST member here that was never
        # in the other roster. It did not migrate into this category; it was
        # authored into it, against the current SDK surface rather than derived
        # from the frozen cp-04 specimen it succeeds.
        #
        # THE RULING AUTHORIZED THE MOVE; THE TREE PROVED IT, and the two were
        # kept in that order deliberately. Measured before this line was
        # written: `shape_of` reads `"canonical"`, and
        # `_sdk_supplied_operator_set` answers True on all five conditions with
        # the factory's plan sources reading `(('required',),)` — no
        # `ccf.projection-requirements`, a named `plan_factory` whose only
        # operator source is the resolver's own tuple, no competing operator
        # set, and no `run_gates` / `build_replay_record` / `serve` anywhere in
        # the tree. This entry records what the predicate already answers; it is
        # not what makes the answer true.
        "examples/cp-04-canonical-corporate-family-tree",
        # `D-IMPL-315` (Dave, 2026-09-10) — rung 6, authored on this side of the
        # boundary like its rung-4 sibling rather than migrated onto it.
        #
        # THE RULING AUTHORIZED THE MOVE; THE TREE PROVED IT, in that order.
        # Measured before this line was written: `shape_of` reads `"canonical"`,
        # `print_problems` is empty, and `_sdk_supplied_operator_set` answers
        # True on all five conditions with plan sources `(('required',),)` — no
        # `ccf.projection-requirements`, a named `plan_factory` whose only
        # operator source is the resolver's own tuple, and no `run_gates` /
        # `build_replay_record` / `serve` anywhere in the tree. This entry
        # records what the predicate already answers.
        "examples/cp-06-collateral-and-setoff-coverage",
        # `D-IMPL-315` (Dave, 2026-09-10) — rung 7, authored on this side of the
        # boundary like its rung-4 and rung-6 siblings rather than migrated onto
        # it.
        #
        # THE RULING AUTHORIZED THE MOVE; THE TREE PROVED IT, in that order, and
        # the measurement came first. Before this line was written: `shape_of`
        # reads `"canonical"`, `resolver_ownership` finds the one
        # `build_governed_resolver` call, `governed_seam_calls` is empty,
        # `legacy_governance_regions` is empty, and
        # `_sdk_supplied_operator_set` answers True with plan sources
        # `(('required',),)` — no `ccf.projection-requirements`, a named
        # `plan_factory` whose only operator source is the resolver's own tuple,
        # and no `run_gates` / `build_replay_record` / `serve` anywhere in the
        # tree. This entry records what the predicate already answers; it is not
        # what makes the answer true.
        "examples/cp-07-client-360-coverage-graph",
        # `D-IMPL-141` admission ruled by Dave, 2026-09-12 — rung 8, and the
        # entry is a ROSTER change only: no line of `examples/cp-08-…` moves
        # with it and `D-IMPL-141` is not reinterpreted. Dave's basis, in his
        # own order:
        #
        #   - the red exists on `origin/main`, so it is not introduced by
        #     `D-IMPL-331` or `D-IMPL-332` — verified by checkout, not inferred;
        #   - cp-08 already claims the approved `D-IMPL-141` SDK-supplied
        #     exemption;
        #   - `shape_of == "canonical"` proves the required canonical form;
        #   - governed-resolver ownership is proven;
        #   - no local governance region or substitute implementation is being
        #     concealed by the exemption.
        #
        # THE RULING AUTHORIZED THE MOVE; THE TREE PROVED IT, in that order and
        # with the measurement taken first. Before this line was written:
        # `shape_of` reads `"canonical"`, `resolver_ownership` finds the one
        # `build_governed_resolver` call at `produce.py:128`,
        # `governed_seam_calls` is empty, `legacy_governance_regions` is empty,
        # `print_problems` is empty, and `_sdk_supplied_deployments()` already
        # names this root. This entry records what the predicate answers; it is
        # not what makes the answer true.
        #
        # WHY IT SAT UNROSTERED. cp-08 shipped canonical at `D-GATE-cp-08` and
        # nobody added the line, so `test_the_sdk_supplied_exemption_has_not_spread`
        # has been red on `main` since. The gap was found by rung 9 tripping
        # the same assertion, which is the roster working as designed: a claim
        # the Control Plane cannot see is red until a human rules on it.
        "examples/cp-08-covenant-in-force-as-of",
        # `D-IMPL-141` admission ruled by Dave, 2026-09-12 — rung 9, and
        # **admitted on its own evidence rather than on rung 8's**. Dave's
        # instruction is why this entry repeats a measurement instead of citing
        # the line above it: *"I would not phrase cp-09 as inheriting cp-08's
        # admission; each product should remain independently evidenced even
        # when both exercise the same SDK seam."* Two roots exercising one seam
        # is not one fact about two roots.
        #
        # THE RULING AUTHORIZED THE MOVE; THE TREE PROVED IT, in that order,
        # and the measurement was taken with cp-08 ALREADY ROSTERED — so this
        # root was the only remaining claimant at the moment it was read, which
        # is what makes the reading about cp-09 and nothing else. Before this
        # line was written: `shape_of` reads `"canonical"`,
        # `resolver_ownership` finds the one `build_governed_resolver` call at
        # `produce.py:118`, `governed_seam_calls` is empty,
        # `legacy_governance_regions` is empty, `print_problems` is empty, and
        # `_sdk_supplied_deployments()` names this root.
        #
        # The deployment authors no operator set at all: `produce.py`'s named
        # `plan_factory` passes the resolver's own `required` tuple straight
        # through to `TreasuryLiquidityProjection`, which returns it unchanged
        # from `required_operators()`. There is nothing to diverge from and no
        # divergence guard to call — the condition `D-IMPL-141` describes,
        # rather than a property this entry asserts.
        "examples/cp-09-treasury-liquidity-position",
        # `D-GATE-cp-10`, 2026-09-12 — rung 10, admitted on its OWN evidence
        # rather than by resemblance to rung 9, which is how cp-08 and cp-09
        # were each admitted in turn. Measured before this line was written:
        # the detector's tree-derived set differed from this roster by exactly
        # this one root and by nothing else — `roster today is missing:
        # ['examples/cp-10-rating-and-spread-migration']`, `has extra: []`.
        #
        # The deployment authors no operator set at all: `produce.py`'s named
        # `plan_factory` passes the resolver's own `required` tuple straight
        # through to `RatingSpreadMigrationProjection`, which returns it
        # unchanged from `required_operators()`. There is nothing to diverge
        # from and no divergence guard to call — the condition `D-IMPL-141`
        # describes, rather than a property this entry asserts. That the
        # SDK-side guard nonetheless refuses a divergent set is separately
        # evidenced: `RSM-G01` and `RSM-G02` are recorded `unavailable`
        # precisely because `D-IMPL-86` fires at BIND before this deployment
        # can produce an artifact.
        "examples/cp-10-rating-and-spread-migration",
        # `D-GATE-cp-11`, 2026-09-12 — rung 11, admitted on its OWN evidence
        # and measured before this line was written: the detector's
        # tree-derived set differed from this roster by exactly this one root
        # and by nothing else — `roster is missing:
        # ['examples/cp-11-credit-surveillance-early-warning']`,
        # `has extra: []`.
        #
        # The deployment authors no operator set at all: `produce.py`'s named
        # `plan_factory` passes the resolver's own `required` tuple straight
        # through to `CreditSurveillanceProjection`, which returns it unchanged
        # from `required_operators()`. There is nothing to diverge from and no
        # divergence guard to call — the condition `D-IMPL-141` describes,
        # rather than a property this entry asserts. That the SDK-side guard
        # nonetheless refuses a divergent set is separately evidenced:
        # `EWS-G01` and `EWS-G02` are recorded `unavailable` precisely because
        # `D-IMPL-86` fires at BIND before this deployment can produce an
        # artifact.
        "examples/cp-11-credit-surveillance-early-warning",
    }
)

#: What :class:`ccf.projection.plan.ProjectionPlan` is structural **about**,
#: quoted from its own docstring: *"Any type exposing ``required_operators()``
#: and ``invoke()`` is a projection. There is no base class to inherit and no
#: registry decorator to remember."* A class whose body defines both is a
#: projection by the SDK's own definition of the word, whatever it is called —
#: which is why the primary recognition of a plan construction keys on this and
#: not on a name (CR-F1).
PLAN_PROTOCOL_MEMBERS: frozenset[str] = frozenset({"required_operators", "invoke"})

#: The constructor keywords every plan in the suite is built with. ``plan_id``
#: is the one identifier ``ProjectionPlan`` names as a member; ``required``
#: carries the operator set the plan declares and is the value property (1)
#: reads. Together they are the second name-independent recognition, and they
#: were measured across ``src/``, ``runtime/``, ``examples/`` and ``tests/``:
#: fourteen calls pass both, and all fourteen are plan constructions.
#: ``required`` **alone** is not discriminating — sixty-seven calls pass it,
#: fifty-three of which are ``argparse`` and other unrelated APIs, one of them in
#: ``examples/`` itself, so keying on it alone would be red on correct code.
PLAN_ID_KEYWORD = "plan_id"
PLAN_REQUIRED_KEYWORD = "required"

#: The pre-CR-F1 rule, kept only as a third net — see
#: :func:`_is_plan_construction`.
PLAN_CLASS_SUFFIX = "Plan"

#: The engine call, and the keyword that makes it a *projection* execution
#: rather than a workflow or a database one — ``engine.execute(workflow, ...)``
#: in examples 05 and 06 is neither, and passes no ``plan``.
ENGINE_EXECUTE_METHOD = "execute"
ENGINE_PLAN_KEYWORD = "plan"

#: Calls that are transparent to the value they wrap. A one-argument set
#: conversion around one side of the collapse does not make it a second source,
#: and neither does a ``cast`` — which is a no-op at runtime. Any *other*
#: callee is a helper, and a helper's return value is out of reach by design
#: (see the docstring).
TRANSPARENT_CONVERSIONS: frozenset[str] = frozenset(
    {"frozenset", "set", "tuple", "list", "sorted"}
)
TRANSPARENT_CAST = "cast"

#: The last element of a path that ends in a method call, so that
#: ``execution.resolved`` (the member) and ``execution.resolved()`` (what it
#: returned) are not silently the same path. It contains characters no
#: identifier can, so it can never collide with a real member name.
CALL_MARKER = "()"

#: One gate call site per body that serves a product — **twelve**, counted from
#: the tree by executing :func:`_gate_scopes`: examples 00, 01, 02, 03,
#: ``04-cross-process/producer_child.py``, 06, 07 and 08, plus
#: ``archive/examples/external/00-hello-context/serve.py``, the two spine examples
#: ``s1-00-companies-over-revenue/produce.py`` and
#: ``s1-01-hello-context-product/spine.py``, and — added in Phase 17 —
#: ``src/ccf/products/resolver.py::GovernedResolver.__call__``, the first
#: in-SDK site, which exists because ``17-03`` moved the assemble→gate→serve
#: composition into the library.
#:
#: **No headroom, on purpose**, and this constant has now been two sites short
#: TWICE. The first time it read 9 against a tree of 11. The second was Phase
#: 17 itself: ``GovernedResolver.__call__`` arrived and the floor stayed at 11,
#: so the phase that documented this failure mode re-opened it. Measured at the
#: close review — 12 sites against a floor of 11, one site of headroom, in a
#: constant whose own comment calls headroom "the quiet form" this module
#: refuses. Raised to 12 under Dave's ruling of 2026-08-16.
#:
#: The lesson the two misses share: **a floor is only a floor while it equals
#: the count.** Adding a witness without raising it converts an assertion into
#: a formality, and nothing goes red to say so.
MINIMUM_GATE_CALL_SITES = 12

#: Bodies that construct a plan and execute it — **fourteen**, counted from the
#: tree by executing :func:`_projecting_scopes`, including the two replay
#: environments' ``resolve_plan`` methods which construct one and return it
#: (``archive/examples/06-decision-replay/run.py``, which contributes two bodies, and
#: ``archive/examples/external/00-hello-context/run.py``), and — added in Phase 17 —
#: ``examples/hw1-companies-over-revenue/deployment/projection.py::build_projection``,
#: the client example's one permitted Python module.
#:
#: This comment's previous revision ended: *"A floor whose comment describes a
#: tree that no longer exists is the quiet form of headroom this module
#: refuses."* It then described exactly such a tree. ``build_projection`` landed
#: in ``17-09`` and the floor stayed at 13, leaving one body of headroom — a
#: regression could have deleted a projecting body and stayed green. Measured at
#: the Phase 17 close review; raised to 14 under Dave's ruling of 2026-08-16.
#:
#: The failure is not that the number was wrong. It is that **the plan which
#: adds a witness is the plan that must raise the floor**, and neither this one
#: nor the gate-site floor above was raised by the work that moved it.
MINIMUM_PROJECTING_BODIES = 14

#: Binder call sites where this module can actually **read** which document the
#: handed plan's ``required=`` came from — the input the argument checks in
#: :func:`_binder_collapses` consume. The two coverage floors above say bodies
#: were found; this one says the argument checks were handed something to
#: compare. A tripwire matching bodies it can say nothing about is the CR-03
#: failure mode restated, so it is asserted rather than assumed.
#:
#: **Twelve, counted from the tree**, against fourteen projecting bodies: one
#: readable site per binder call, with ``archive/examples/06-decision-replay/run.py``
#: and ``archive/examples/external/00-hello-context/`` each contributing two (a serving
#: body and a ``resolve_plan``), and **zero** unreadable. Twelve sites therefore
#: sit in ELEVEN files, and the **three** projecting bodies making no binder
#: call at all are exactly the exempt ones —
#: ``examples/s1-00-companies-over-revenue/produce.py`` and
#: ``examples/cp-00-institutional-holders/produce.py`` under D-IMPL-137, and
#: ``examples/hw1-companies-over-revenue/deployment/projection.py`` under
#: `D-IMPL-141`. Re-counted 2026-08-27 when ``cp-00`` landed: the prior text
#: said *thirteen* bodies with ``s1-00`` the only abstainer, which was true when
#: written and had stopped being true here. The previous value of 11 was one
#: site short of the tree.
#:
#: **This floor now sits on the exemption's path, which it did not before
#: D-IMPL-137.** A one-document deployment legitimately removes a binder call,
#: so a *further* deployment claiming the exemption would take the readable
#: sites 12 -> 11 and leave a floor of 11 green. What actually catches that
#: case is :data:`RULED_ONE_DOCUMENT_DEPLOYMENTS`, which names its claimants
#: and is red at :func:`test_the_one_document_exemption_has_not_spread`
#: on an unruled one. This floor is therefore redundant defence there
#: rather than the primary control — but the adjacency is new, and is stated
#: rather than left to be rediscovered by whoever next lowers this number.
MINIMUM_RESOLVED_BINDER_SITES = 11

#: The SDK module whose own binder call is the canonical path's evidence.
#: `D-IMPL-300` put `refuse_operator_set_divergence` at the ruled pre-execution
#: point inside `GovernedResolver`; this names the file so the assertion below
#: reads it rather than trusting that it is still there.
CANONICAL_BINDER_MODULE = "src/ccf/products/resolver.py"

#: Projecting bodies whose binder call is the SDK's rather than their own —
#: **two** today (`examples/cp-05-credit-exposure-rollup/produce.py` and
#: `examples/s1-01-hello-context-product/spine.py`), counted from the tree by
#: :func:`_delegated_binder_sites`.
#:
#: **THE EVIDENCE SPLITS BY ARCHITECTURAL OWNERSHIP** (`D-IMPL-307`). Before
#: `D-IMPL-300` there was one population and one floor, because there was one
#: way for a deployment to bind its authored operator set to the class's claim:
#: call the binder. A deployment that adopts
#: :func:`~ccf.products.resolver.build_governed_resolver` no longer calls it —
#: the resolver does, on the deployment's behalf, at the ruled point. A single
#: total cannot tell *"an example stopped binding"* from *"an example handed
#: binding to the SDK"*, and those two need opposite responses.
#:
#: So the two are counted separately and each floor sits at its own observed
#: count with no headroom. An example migrating moves ONE site from
#: :data:`MINIMUM_RESOLVED_BINDER_SITES` to this constant; both edits land in
#: the same commit, and a lone decrement with no matching increment is the
#: regression the split exists to expose.
#:
#: **The credit is CONTINGENT, never free.** :func:`_delegated_binder_sites`
#: returns nothing at all unless :func:`_canonical_binder_ownership` can read
#: the SDK's own binder call. Delete that call and every delegated site stops
#: counting at once — which is the property a bare "this example delegates"
#: check would not have.
# `D-IMPL-309`'s modernization pass moved `s1-01` across on 2026-09-09: its
# own binder call at `examples/s1-01-hello-context-product/spine.py` — the last
# one in the live `examples/` tree, and the whole of `MOD-01` — is gone because
# `GovernedResolver` now performs it on the deployment's behalf. Resolved
# 12 -> 11 and delegated 1 -> 2, in this one commit, which is the paired edit
# the split above exists to require.
MINIMUM_DELEGATED_BINDER_SITES = 2

#: Every floor here is the count observed in the tree, with **no headroom, on
#: purpose** — see :func:`test_the_binder_scan_is_not_vacuous` for why headroom
#: would be a licence to lose a call site silently, and what a legitimate
#: removal is required to leave behind instead.
FLOOR_REMOVAL_INSTRUCTION = (
    "A DELIBERATE removal and an accidental one need the identical edit to this"
    " constant, so nothing at this failure site distinguishes them. Lower the"
    " constant in the same commit as the removal and name the removed site in"
    " the commit message — `git log` is then the only thing that tells the two"
    " apart afterwards."
)


# --- source discovery ---------------------------------------------------------


def _python_sources(trees: tuple[str, ...]) -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for tree in trees:
        found.extend(sorted((REPO_ROOT / tree).rglob("*.py")))
    return found


def _parse(path: pathlib.Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - a broken file fails elsewhere
        return None


def _scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """Every node in one lexical body, not descending into nested bodies.

    ``ast.walk`` would reach into nested functions and class bodies, which for
    tripwire (1) is not a widening but an error: it would pair a ``run_gates``
    call in one method with a ``ProductLineage`` construction in another and
    report a collapse that is not there. One body means one body.
    """
    stack: list[ast.AST] = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(
            node,
            ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda,
        ):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _scopes(tree: ast.Module) -> list[ast.AST]:
    """Every lexical body in a module: the module, each function, each class, each lambda.

    **Classes and lambdas are here because :func:`_scope_nodes` refuses to
    descend into them** (R4-IN-01). That refusal is right — a ``run_gates`` call in
    one method must not pair with a ``ProductLineage`` construction in another —
    but it means a body this function does not *list* is scanned by nothing at
    all. A plan constructed in a class body or a lambda was then not "scanned
    and unresolvable", which the limits list covers; it was invisible, and
    ``MINIMUM_PROJECTING_BODIES`` could not see it either, because the body never
    entered the count. Measured 2026-08-06 before widening: **zero** class
    bodies and **zero** lambda bodies under ``examples/`` construct or run a
    projection, and **zero** under ``src/``/``runtime/``/``examples/`` call
    ``run_gates``, so no floor and no verdict moves — the widening closes a claim
    rather than changing an answer.

    One imprecision, stated: a ``lambda``'s *default* argument expressions are
    evaluated in the enclosing body, not in the lambda, and they are counted
    here as the lambda's because ``ast.iter_child_nodes`` puts them under
    ``args``. That misattributes which body they belong to; it cannot hide them,
    which is the direction that matters.
    """
    bodies: list[ast.AST] = [tree]
    for node in ast.walk(tree):
        if isinstance(
            node,
            ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda,
        ):
            bodies.append(node)
    return bodies


def _scope_label(scope: ast.AST) -> str:
    if isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef):
        return f"{scope.name}()"
    if isinstance(scope, ast.ClassDef):
        return f"class {scope.name}"
    if isinstance(scope, ast.Lambda):
        return "<lambda>"
    return "<module>"


def _scope_line(scope: ast.AST) -> int:
    return getattr(scope, "lineno", 1)


# --- source positions ---------------------------------------------------------


def _at(node: ast.AST) -> tuple[int, int]:
    """Where ``node`` starts, as ``(line, column)``.

    **A line number is not a position, and the difference is a whole class of
    defect.** Two statements separated by a semicolon share a line; a compound
    statement and the suite written on its own header line share a line; a
    comprehension and an expression beside it share a line. A model that orders
    bindings and reads by line alone answers all three wrong — in the first two
    by leaving the *previous* binding in force (R4-CR-01, the affirmative answer),
    and in the third by putting a binding in force outside its own scope (R4-WR-01,
    red on correct code). Ordering ``(line, column)`` tuples separates all three,
    because for the statements and top-level expressions this module compares,
    left-to-right source order **is** evaluation order.

    Where it is not: a comprehension evaluates its outermost iterable before its
    element expression, though the element is written first; a ``lambda`` body
    runs at call time, not where it sits. Both are named in the module
    docstring's limits list rather than modelled.
    """
    return (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))


def _after(node: ast.AST) -> tuple[int, int]:
    """The position immediately past ``node``'s last character.

    What a binding's *effective* position is built from, and the reason it is
    not simply the statement's start: Python evaluates the value before it binds
    the target. ``plan = build(plan)`` reads the **old** ``plan``, and so does

    .. code-block:: python

        plan = FixturePlan(
            plan_id=pid,
            required=plan.required_operator_keys,   # the OLD plan
        )

    Anchoring the binding past the value expression is what gets both right,
    the multi-line spelling included — where a start-anchored line model put the
    new binding in force on lines 2 and 3 of its own right-hand side.

    Falls back to the start position for a node carrying no end, which no node
    this module asks about does under the Python versions the project supports;
    the fallback exists so a future node shape degrades to the old answer rather
    than to an exception.
    """
    line = getattr(node, "end_lineno", None)
    column = getattr(node, "end_col_offset", None)
    if line is None or column is None:
        return _at(node)
    return (line, column)


# --- identifier paths ---------------------------------------------------------


def _is_transparent(node: ast.Call) -> bool:
    """A call that is a no-op over the value it wraps."""
    return (
        isinstance(node.func, ast.Name)
        and bool(node.args)
        and (
            node.func.id in TRANSPARENT_CONVERSIONS
            or (node.func.id == TRANSPARENT_CAST and len(node.args) > 1)
        )
    )


def _unwrap(node: ast.expr) -> ast.expr:
    """``(name := expr)`` seen as ``expr``, which is the value it evaluates to.

    A walrus binds *and* evaluates: ``(plan := FixturePlan(...))`` is the plan it
    just constructed, and every question this module asks of an argument
    expression — is this a plan construction, which document is its ``required=``
    built from — is a question about that construction.

    Without this, wrapping a construction in a walrus routed it past property
    (2)'s hoist branch entirely (R4-WR-02): ``plan_node`` was an ``ast.NamedExpr``
    rather than an ``ast.Call``, so the branch did not fire, ``_binding_path``
    then returned ``None`` for the same node, and the execution took the
    ``execution.plan is None`` quiet exit — while ``_plan_sources`` had already
    recorded the construction's source and held it. The module knew and said
    nothing, which is the shape of every finding this phase has produced.
    """
    while isinstance(node, ast.NamedExpr):
        node = node.value
    return node


def _path(node: ast.expr) -> tuple[str, ...] | None:
    """The dotted identifier path an expression reads, if it has one.

    ``execution.operators_invoked`` yields ``("execution", "operators_invoked")``;
    ``frozenset(declared.required_operator_keys)`` yields
    ``("declared", "required_operator_keys")``, because a set conversion is
    transparent to its argument; ``self._declared`` yields
    ``("self", "_declared")``, which is what keeps two attributes of one object
    distinguishable.

    A **method call** yields its receiver's path extended by the method name and
    :data:`CALL_MARKER`: ``execution.resolved()`` is
    ``("execution", "resolved", "()")``. Both halves of that spelling are
    load-bearing and were each found the hard way (WR-02, then WR-F4):

    * Keeping the **member name** is what stops the collapse WR-02 removed.
      Reading ``obj.method()`` as bare ``("obj",)`` makes *any* method call on
      an object share a source with *any* attribute read of it, so
      ``self.declared_claim()`` paired with ``self._resolved`` was reported as a
      collapse and the check was **red on correct code**. With the member in the
      path the two differ in their second element, and
      :func:`_shares_a_source`'s prefix rule keeps them apart.
    * Keeping **any** path at all is what stops the false *negative* WR-02's fix
      introduced. Returning ``None`` here admitted ``execution.resolved()`` on
      both sides of Gate 2 — one expression, one value, compared against itself.

    What is still out of reach: a helper's return value (``derive(execution)``
    roots at the helper and stops), what a method *returns* rather than which
    method it is (``a.keys()`` and ``a.key_set()`` are two paths whatever they
    return), a subscript, and a dynamic attribute access. Each yields ``None``
    and the module docstring names it as a limit rather than pretending
    otherwise.
    """
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        base = _path(node.value)
        return None if base is None else (*base, node.attr)
    if isinstance(node, ast.NamedExpr):
        return _path(node.value)
    if isinstance(node, ast.Await):
        return _path(node.value)
    if isinstance(node, ast.Call):
        if _is_transparent(node):
            index = 1 if _callee(node) == TRANSPARENT_CAST else 0
            return _path(node.args[index])
        if isinstance(node.func, ast.Attribute):
            base = _path(node.func.value)
            return None if base is None else (*base, node.func.attr, CALL_MARKER)
        # A free function's return value is out of reach: `derive(x)` roots at
        # `derive`, and nothing in an AST walk says what it does with `x`.
        return None
    return None


def _render(path: tuple[str, ...]) -> str:
    """A resolved path spelled the way a reader would write it."""
    text = ""
    for element in path:
        if element == CALL_MARKER:
            text += CALL_MARKER
        elif text:
            text = f"{text}.{element}"
        else:
            text = element
    return text


def _assignment(node: ast.AST) -> tuple[list[str], ast.expr | None]:
    """Names bound to one **whole** value expression, and that expression.

    A narrower question than :func:`_binding_records`, and deliberately so: this
    is the only shape a *plan construction* can be read out of, so it is what
    :func:`_plan_sources` consumes. ``plan = FooPlan(...)`` binds one name to one
    call and the call is right there; ``plan, spare = FooPlan(...), None`` binds
    ``plan`` to an *element* of a tuple, and which element is a question this
    returns nothing about rather than guessing at.

    It is **not** the answer to "what does this statement bind" — that is
    :func:`_binding_records`, and reading this one as if it were the other is
    exactly what CR-01 found. A tuple target still *binds*, and the binding map
    records it as unreadable; it just carries no plan source.
    """
    if isinstance(node, ast.Assign):
        return ([t.id for t in node.targets if isinstance(t, ast.Name)], node.value)
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return ([node.target.id], node.value)
    if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
        return ([node.target.id], node.value)
    return ([], None)


def _bound_names(target: ast.expr) -> list[str]:
    """Every **local name** one assignment target binds.

    ``a`` is ``["a"]``; ``a, b`` is ``["a", "b"]``; ``a, *rest`` is
    ``["a", "rest"]``; ``[a, (b, c)]`` is all three, because unpacking nests.

    ``obj.attr`` and ``d["k"]`` return ``[]``, and that is not the same omission
    CR-01 was about. They bind a **member**, not a local name, and this module's
    binding map is keyed by local name — so nothing was ever bound to
    ``obj.attr`` here and a read of it resolves to the literal path
    ``("obj", "attr")`` rather than to a stale value. The residual is that such a
    write is not *followed*; it cannot leave a wrong binding in force, which is
    what makes it a limit rather than the defect.
    """
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Tuple | ast.List):
        return [name for element in target.elts for name in _bound_names(element)]
    if isinstance(target, ast.Starred):
        return _bound_names(target.value)
    return []


def _opaque(name: str, position: tuple[int, int]) -> str:
    """A source token for a name whose binding this module cannot read through.

    ``plan = QuickstartPlan(...)`` binds ``plan`` to a value no identifier path
    describes. The binding is still a *source*, and it is the source of every
    read of ``plan`` until the next assignment to it — so the token carries the
    **position** of the binding, which makes two assignments to one name two
    sources and one assignment one source. That is precisely the object identity
    property (2) needs, and it is why the token is a path element rather than a
    separate model.

    Spelled ``name@line:column`` — ``plan@231:11`` — so a failure message names
    the assignment it means rather than only the identifier. The column is not
    decoration: keyed on the line alone, ``plan = A(); bind(plan=plan);
    plan = B(); run(plan=plan)`` written on one physical line gives both
    constructions the token ``plan@4``, so property (2) matches the second
    execution against the first call's binder and reports the unbound plan as
    bound — CR-01's inversion moved into the token space.
    """
    return f"{name}@{position[0]}:{position[1]}"


def _binding_path(value: ast.expr) -> tuple[str, ...] | None:
    """What a name bound to ``value`` should be *followed* to, if anything.

    Not the same question as :func:`_path`, and the difference is deliberate. A
    call **evaluates to a new value each time it runs**, so a name bound to one
    is bound to that evaluation and to nothing else: two constructions of one
    plan class are two objects, and following both to the same class path would
    make property (2) believe the binder bound the plan the engine ran when it
    bound the other one. Transparent conversions are the exception, because
    ``frozenset(x)`` is a view of ``x`` rather than an independent value.

    :func:`_path` still reads a method call as a path, and must: two *reads* of
    ``execution.resolved()`` in one body are the same expression and Gate 2
    comparing them is comparing a value against itself (WR-F4). The asymmetry is
    that following an alias asks "which object is this name", while reading an
    argument asks "what does this expression read".
    """
    if isinstance(value, ast.Call) and not _is_transparent(value):
        return None
    return _path(value)


class _Binding(NamedTuple):
    """One binding of one local name, by any of the forms Python has.

    ``position`` is ``(line, column)`` and it is where the binding **takes
    effect**, which is not where its statement starts. Python evaluates before
    it binds, so an assignment's binding is anchored past its value expression
    and a ``for``'s past its iterable — see :func:`_after` and
    :func:`_binding_records` for the form-by-form table. Recording the
    statement's start instead is what made a read inside a multi-line right-hand
    side resolve to the binding that right-hand side is still computing.

    ``path`` is where the bound value reads, or ``None`` when this module cannot
    read through it. **``None`` means present-but-unreadable, never absent** —
    that distinction is the whole of CR-01. A binding that is recorded as
    unreadable makes the downstream checks say "I cannot tell" (loudly, via
    :func:`_opaque`'s per-position token); a binding that is not recorded at all
    leaves the *previous* binding in force and makes them answer affirmatively
    about a value that is no longer there.

    ``until`` is set only for a **comprehension target**, whose binding does not
    escape the comprehension in Python 3. It is the position immediately past
    the comprehension expression, so ``position``/``until`` is the
    comprehension's **lexical span** and containment in it is exactly Python's
    scope rule. It was a pair of *line numbers* for one round, which over-covered
    every expression sharing the comprehension's first or last line: R4-WR-01
    measured a correct ``return ([str(plan) for plan in alts],
    engine.execute(plan=plan))`` reported red, and a genuine tripwire-(1)
    collapse on such a line reported quiet. Every ``until``-carrying binding is
    constructed with ``path=None``, which is what keeps :func:`_resolve_at`
    terminating — see :func:`_binding_before`.
    """

    position: tuple[int, int]
    path: tuple[str, ...] | None
    until: tuple[int, int] | None = None

    @property
    def lineno(self) -> int:
        """The line ``position`` falls on — for failure messages and floors."""
        return self.position[0]


def _binding_records(node: ast.AST) -> Iterator[tuple[str, _Binding]]:
    """Every local name one node binds, and what it binds it to.

    **This is CR-01's fix and the enumeration is the fix.** Its predecessor read
    three forms — ``Assign`` with ``Name`` targets, ``AnnAssign``, ``NamedExpr``
    — and *silently bound nothing* for the rest, so a plan local rebound by a
    tuple unpack, a ``for`` target, a ``with ... as``, an ``except ... as`` or an
    augmented assignment kept its previous binding and the checks reported on the
    object that binding named. Every assertion in the module passed on a body
    running an unbound plan built from the binder's own ``declared=``.

    A form this module cannot read *through* is recorded with ``path=None``
    rather than skipped. That is the difference between "the plan the engine runs
    is one I cannot describe" — which property (2) reports — and "the plan the
    engine runs is the one the binder was handed", which is what the gap said.

    What binds, what it binds to, and **where the binding takes effect**. The
    third column is not bookkeeping: Python evaluates before it binds, so a
    binding anchored at its statement's start is in force over source that runs
    before it exists, and a binding anchored at its statement's *line* is not in
    force over a suite written on that same line — which is the affirmative
    stale answer CR-01 is about, one layer down (R4-CR-01).

    * ``a = expr`` / ``a = b = expr`` — the value's path, if it has one. In force
      past ``expr``, so ``a = f(a)`` and a multi-line right-hand side that reads
      ``a`` both see the previous binding.
    * ``a: T = expr`` — the same. A bare ``a: T`` binds nothing and is skipped,
      which is what Python does.
    * ``(a := expr)`` — the same.
    * ``a, b = …`` / ``[a, b] = …`` / ``a, *rest = …`` — every name, unreadable:
      each is bound to an *element*, and which element is not a question an
      identifier path answers. In force past the value.
    * ``a += expr`` — unreadable. The new value derives from the old and from the
      right-hand side, and is neither; see the limits list in the module
      docstring for what that costs. In force past the right-hand side.
    * ``for a in …`` / ``async for a in …`` — unreadable, in force **past the
      iterable**. Past the iterable and not at the ``for`` keyword, because
      ``for plan in transform(plan):`` reads the previous ``plan`` in its own
      header; past the *iterable* and not at the suite, because
      ``for plan in alts: run(plan)`` is one line and the suite reads the new one.
    * ``with … as a`` / ``async with … as a`` — unreadable, in force past that
      item's context expression, for the same two reasons. ``ast.withitem``
      carries no position of its own, which is why the context expression rather
      than the item is what the position is taken from.
    * ``except E as a`` — unreadable, in force past ``E`` (or from the handler's
      own start when there is none). Python unbinds the name at the end of the
      handler; an opaque token is closer to that than the pre-``try`` value.
    * ``import x`` / ``from m import y as a`` — unreadable, in force past the
      whole statement, which is what makes ``from m import plan; run(plan)``
      resolve to the import. A module object has no identifier path, and
      ``import *`` binds names this cannot enumerate.
    * ``def a`` / ``async def a`` / ``class a`` — unreadable, in force past the
      whole statement; both bind a name in the enclosing body.
    * ``case [a]`` / ``case *a,`` / ``case {**a}`` — unreadable, in force from the
      pattern's own position, which precedes both the guard and the case body —
      the only places the capture is readable.
    * a comprehension's ``for a in …`` — unreadable **and scoped** to the
      comprehension's own **lexical span** (``until``), because in Python 3 the
      target does not leak. Recording it unscoped would be red on the correct
      body ``plan = P(); bind(plan); [g(p) for plan in ps]; run(plan)``;
      recording the span as a pair of *line numbers* was red on the correct body
      ``return ([g(p) for plan in ps], run(plan))`` (R4-WR-01).

    Not bound here, and each named in the module docstring's limits: an
    attribute or subscript target (binds a member, not a local name);
    ``global``/``nonlocal`` (they redirect an assignment, they do not bind);
    ``del`` (unbinds — a subsequent read is a ``NameError``, so a body relying on
    it is broken before this module sees it).
    """
    if isinstance(node, ast.Assign):
        position = _after(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                yield (target.id, _Binding(position, _binding_path(node.value)))
                continue
            for name in _bound_names(target):
                yield (name, _Binding(position, None))
    elif isinstance(node, ast.AnnAssign):
        if node.value is not None and isinstance(node.target, ast.Name):
            yield (
                node.target.id,
                _Binding(_after(node.value), _binding_path(node.value)),
            )
    elif isinstance(node, ast.NamedExpr):
        yield (
            node.target.id, _Binding(_after(node.value), _binding_path(node.value))
        )
    elif isinstance(node, ast.AugAssign):
        for name in _bound_names(node.target):
            yield (name, _Binding(_after(node.value), None))
    elif isinstance(node, ast.For | ast.AsyncFor):
        for name in _bound_names(node.target):
            yield (name, _Binding(_after(node.iter), None))
    elif isinstance(node, ast.With | ast.AsyncWith):
        for item in node.items:
            if item.optional_vars is None:
                continue
            for name in _bound_names(item.optional_vars):
                yield (name, _Binding(_after(item.context_expr), None))
    elif isinstance(node, ast.ExceptHandler):
        if node.name is not None:
            position = _at(node) if node.type is None else _after(node.type)
            yield (node.name, _Binding(position, None))
    elif isinstance(node, ast.Import | ast.ImportFrom):
        position = _after(node)
        for alias in node.names:
            if alias.name == "*":
                continue
            yield (
                alias.asname or alias.name.split(".")[0], _Binding(position, None)
            )
    elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        yield (node.name, _Binding(_after(node), None))
    elif isinstance(node, ast.MatchAs | ast.MatchStar):
        if node.name is not None:
            yield (node.name, _Binding(_at(node), None))
    elif isinstance(node, ast.MatchMapping):
        if node.rest is not None:
            yield (node.rest, _Binding(_at(node), None))
    elif isinstance(node, ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp):
        span = _at(node)
        until = _after(node)
        for generator in node.generators:
            for name in _bound_names(generator.target):
                yield (name, _Binding(span, None, until))


def _bindings(scope: ast.AST) -> dict[str, tuple[_Binding, ...]]:
    """Every binding of every local name in one body, in source order.

    **Order-aware, and every binding kept.** Two predecessors were wrong here in
    two different ways, and the docstring was wrong about both.

    The first recorded one entry per name with ``setdefault`` over a traversal
    that yields statements in *reverse* source order, so it kept the **last**
    textual assignment and applied it to every use of that name anywhere in the
    body while calling itself "the raw first-assignment map". WR-F2 measured both
    consequences: tripwire (1) red on a correct body that reuses an ordinary
    local name, and property (2) blind to a plan local rebound between the bind
    and the execute.

    The second — this function's immediate predecessor — kept every binding in
    order but read only three **spellings** of a binding while stating "every
    assignment to every local name". CR-01 measured that gap: a tuple unpack, a
    ``for`` target, a ``with … as``, an ``except … as`` and an augmented
    assignment each bound nothing, so the previous binding stayed in force and
    the checks reported on it *affirmatively*. A missed binding is worse than an
    unreadable one for exactly that reason, and :func:`_binding_records` is where
    the enumeration now lives.

    A list per name, sorted by **position**, answers the question the checks
    actually ask — *what was this name bound to at the point of use* — and
    :func:`_binding_before` is where that question is put. Sorted by position
    and not by line, because two bindings of one name can share a line
    (``plan = A(); plan = B()``) and a line-keyed order picks between them
    arbitrarily.

    Traversal order is not relied on; the result is sorted explicitly, so this
    is independent of both ``_scope_nodes``'s stack order and dict iteration
    order. The sort key breaks a position tie in favour of a comprehension's
    scoped binding, so the ordering is total and deterministic; Python forbids
    the shape that would make the tie load-bearing (an assignment expression may
    not rebind the comprehension target it sits inside).
    """
    found: dict[str, list[_Binding]] = {}
    for node in _scope_nodes(scope):
        for name, binding in _binding_records(node):
            found.setdefault(name, []).append(binding)
    return {
        name: tuple(
            sorted(
                entries,
                key=lambda binding: (binding.position, binding.until is not None),
            )
        )
        for name, entries in found.items()
    }


def _binding_before(
    name: str, position: tuple[int, int], bindings: dict[str, tuple[_Binding, ...]]
) -> _Binding | None:
    """The binding of ``name`` in force at ``position``: the last one before it.

    Strictly before, so ``x = x.y`` reads the *previous* ``x`` rather than
    itself — and, because a binding is anchored past its own value expression
    (:func:`_after`), so does every read inside that value expression however
    many lines it spans.

    **Positions and not lines.** Comparing ``(line, column)`` is what makes the
    answer track Python for the three shapes that share a line: statements
    separated by ``;``, a compound statement whose suite is written on its own
    header line, and a comprehension beside another expression. A strictly-below
    *line* comparison answered all three by leaving the **previous** binding in
    force — so ``plan = P(); bind(plan=plan); plan = Q(); run(plan=plan)`` and
    ``for plan in alts: run(plan=plan)`` each resolved the run to the *bound*
    plan and reported the body compliant, affirmatively, on nine spellings the
    round before had certified closed (R4-CR-01).

    **A comprehension target is the one exception, and it is scoped rather than
    ordered.** ``[run(plan=p) for p in ps]`` binds and reads ``p`` in one
    expression, so "strictly before" would resolve that read to whatever ``p``
    was before the comprehension — the stale-binding answer CR-01 is about. An
    ``until``-carrying binding is therefore in force for reads **lexically
    inside** the comprehension, ``position <= read < until``, and for no other
    read. Lexical containment and not a line range: a line range over-covers
    every expression sharing the comprehension's first or last line, which was
    red on the correct body ``return ([str(plan) for plan in alts],
    engine.execute(plan=plan))`` and quiet on a genuine tripwire-(1) collapse
    written the same way (R4-WR-01).

    Every ``until``-carrying binding is built with ``path=None``
    (:func:`_binding_records` constructs them nowhere else), so the containment
    branch cannot hand :func:`_resolve_at` a binding it would follow to the same
    position and loop on. Termination is asserted rather than argued, over a
    comprehension that shadows the name it reads, in
    :func:`test_alias_resolution_terminates_on_a_cyclic_assignment_chain`.

    **WITHDRAWN, 2026-08-06 (R4-CR-01).** This docstring previously said that
    the cost of comparing lines rather than positions was that statements
    sharing a line "resolve conservatively — none of them is 'before' the
    others — **which under-resolves rather than mis-resolves**", adding that no
    file in the scanned trees was written that way. Both halves were wrong in
    the direction that matters. It did not under-resolve: it resolved to the
    **previous** binding, affirmatively, which is mis-resolution and is the
    exact failure :func:`_binding_records` was written to remove. And "no file is
    written that way" is an observation about today's tree, not a mechanism —
    nothing in ``make lint`` or in CI refuses a one-line compound suite. The
    sentence is recorded here rather than deleted because a reader comparing
    revisions is entitled to see which claim was retired and why.
    """
    latest: _Binding | None = None
    for binding in bindings.get(name, ()):
        if binding.until is None:
            if binding.position < position:
                latest = binding
        elif binding.position <= position < binding.until:
            latest = binding
    return latest


def _resolve_at(
    path: tuple[str, ...] | None,
    position: tuple[int, int],
    bindings: dict[str, tuple[_Binding, ...]],
) -> tuple[str, ...] | None:
    """Where the value read by ``path`` at ``position`` comes from.

    ``a = execution.operators_invoked`` then ``b = a`` resolves a read of ``b``
    to ``("execution", "operators_invoked")``, so a chain of assignments is
    followed rather than only its first hop — the bypass cross-AI review raised
    against the sibling guard at the Phase 15 close. Each hop resolves the head
    **as of the position that bound it**, not as of the point of use, which is
    what makes the answer the one Python would give.

    **Termination is by construction.** Every hop replaces ``position`` with the
    position of a binding strictly before it, and :func:`_binding_before` only
    ever looks strictly before, so the position at which the walk is asking
    strictly decreases in the tuple order and the walk is bounded by the number
    of bindings in the body. The one branch that answers at a position it is
    already at — a comprehension's scoped target — is unreadable by
    construction and returns immediately.

    The three-name rotation ``def f(b, c): a = b; b = c; c = a`` — legal,
    executable Python that hung the predecessor of this function with no output
    — terminates here in one hop per name and, better than terminating,
    resolves *correctly*: at the bottom of that body ``a`` and ``c`` both hold
    the parameter ``b``, which is what the code does.
    :func:`test_alias_resolution_terminates_on_a_cyclic_assignment_chain` holds
    both properties under a wall-clock bound.

    **What this cannot see is execution order that is not source order**, and
    the case that matters is a loop: a rebinding written *below* a read in the
    same loop body is in force on every iteration after the first, and this
    walk reads it as never in force (R4-WR-03). Named in the module docstring's
    limits list; closing it needs control flow, which an AST walk over one body
    is not.
    """
    if path is None:
        return None
    while True:
        head, *rest = path
        binding = _binding_before(head, position, bindings)
        if binding is None:
            return path
        if binding.path is None:
            return (_opaque(head, binding.position), *rest)
        path = (*binding.path, *rest)
        position = binding.position


def _shares_a_source(
    left: tuple[str, ...] | None, right: tuple[str, ...] | None
) -> bool:
    """One path is the other, or a prefix of it — the same value either way.

    Prefix rather than equality so ``resolved`` and ``resolved.keys`` are not
    treated as two sources; head-only rather than prefix would collapse
    ``self._declared`` and ``self._resolved``, which are two.
    """
    if left is None or right is None:
        return False
    shorter, longer = sorted((left, right), key=len)
    return longer[: len(shorter)] == shorter


# --- the premise: does this deployment have two documents? --------------------


#: The single-file authoring document's canonical name (`D-IMPL-136`;
#: `~ccf.deployment.config.derive_deployment`'s own default `config_filename`).
#: `16-31` converts HW-1 to this form, so a deployment root can hold this file
#: directly with no ``artifacts/`` subdirectory at all — the second shape
#: :func:`_deployment_root` must recognise, alongside the multi-file one.
SINGLE_FILE_CONFIG_NAME = "ccf_config.yaml"


def _deployment_root(path: pathlib.Path) -> pathlib.Path | None:
    """The nearest ancestor of ``path`` under ``examples/`` holding a Control
    Plane authoring surface — either shape `D-IMPL-136`'s dual model permits.

    Returns ``None`` for a body with no artifact tree — a synthesized fixture
    under ``tmp_path``, or a tree outside ``examples/``. That answer is
    load-bearing: see :func:`_one_document` for why it is fail-closed.
    """
    examples = REPO_ROOT / "examples"
    for candidate in (path.parent, *path.parents):
        if not candidate.is_relative_to(examples):
            return None
        if (candidate / "artifacts").is_dir():
            return candidate
        if (candidate / SINGLE_FILE_CONFIG_NAME).is_file():
            return candidate
    return None


def _registers_requirements(root: pathlib.Path | None) -> bool:
    """Whether this deployment registers a ``ccf.projection-requirements``.

    Any YAML in the artifact tree, because the manifest's filename varies —
    ``archive/examples/04-cross-process`` declares it in ``producer-manifest.yaml``.
    A single-file deployment's ``ccf_config.yaml`` is scanned the same way:
    it can never actually carry this registration (`ccf.projection-requirements`
    is not one of `D-IMPL-136`'s eight reserved section names — see
    `~ccf.deployment.config`'s own module docstring, *"there is no
    `signal_batch` section, and that is a decision, not a gap"*, the same
    reasoning that applies here), so this always answers `False` for one —
    scanned rather than assumed, on the same discipline every other reading
    in this module reads the tree instead of trusting a claim about its shape.
    """
    if root is None:
        return False
    documents = list((root / "artifacts").rglob("*.yaml"))
    single_file = root / SINGLE_FILE_CONFIG_NAME
    if single_file.is_file():
        documents.append(single_file)
    return any(
        REQUIREMENTS_REGISTRATION_RE.search(document.read_text(encoding="utf-8"))
        for document in documents
    )


def _class_claim(
    scope: ast.AST, bindings: dict[str, tuple[_Binding, ...]]
) -> tuple[str, ...] | None:
    """Where this body's product-class operator claim reads.

    Row A reads it from the binder's own ``declared=``. Rows B and C have no
    binder call, so it comes from ``ProductLineage(operators_invoked=…)`` —
    already this module's anchor for the product's side of Gate 2.

    ``None`` where no lineage is assembled: the two replay environments'
    ``resolve_plan`` methods construct a plan and return it. Those bodies are
    subject to the demand (:func:`_one_document`), and both sit in
    two-document deployments, so nothing about them moves.
    """
    for node in _scope_nodes(scope):
        if not (isinstance(node, ast.Call) and _callee(node) == LINEAGE_CONSTRUCTOR):
            continue
        argument = _keyword(node, LINEAGE_DECLARED_KEYWORD)
        if argument is not None:
            return _resolve_at(_path(argument), _at(argument), bindings)
    return None


def _config_declares_operator_set(root: pathlib.Path | None) -> bool:
    """Whether this deployment authors its operator set in the ONE config document.

    The positive half of `D-IMPL-234`'s first condition: the single authored
    side EXISTS and is readable on disk, in the `D-IMPL-136` section the SDK
    reserves for it, carrying a non-empty operator list. A deployment that
    declares no product class, or declares one with no operator set, has not
    authored the one document this route is about and gets nothing from it.

    Read from the config rather than assumed from the *absence* of a
    requirements artifact, which is the whole discipline `D-IMPL-234` insists
    on: *"never by the inference `no binder call implies exempt`."* Absence of a
    second document is necessary but it is not sufficient, and on its own it is
    indistinguishable from `D-IMPL-137` row C — a second set authored where the
    Control Plane cannot see it.

    Parsed plainly rather than through
    :func:`~ccf.deployment.config.derive_deployment`, for the reason
    :func:`_binding_plan_reference` gives for the same choice: that loader
    validates the whole document, so an unrelated authoring mistake would take
    this gate down with it and report a wiring typo as a binder-coverage
    failure. Only the one section is read; its *name* still comes from the SDK.
    """
    if root is None:
        return False
    document = root / SINGLE_FILE_CONFIG_NAME
    if not document.is_file():
        return False
    try:
        parsed = yaml.safe_load(document.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return False
    if not isinstance(parsed, dict):
        return False
    section = parsed.get(PRODUCT_CLASS_SECTION)
    if not isinstance(section, dict):
        return False
    declared = section.get(PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE)
    return isinstance(declared, list) and bool(declared)


def _supplied_by_the_product_class(
    scope: ast.AST,
    path: pathlib.Path,
    root: pathlib.Path | None,
    plan_classes: frozenset[str] | None = None,
) -> bool:
    """`D-IMPL-234`: the plan's ``required=`` is SUPPLIED by the one authored
    document, not authored a second time.

    **The second shape a one-document deployment can take, and the reason the
    detector had to be taught rather than the roster appended to.** Dave, at the
    2026-09-01 close-panel triage: *"Do not call the binder. Do not slip cp-04
    onto the exemption list as a quiet edit. The binder's premise is two
    documents that can disagree. cp-04 has one authored side; ``required`` would
    be compared to itself. That is the tautology you already refused after
    17-13."* The premise is learned **by positive conditions** — his words for
    what this route reads — *"the plan/binding names the one projection and
    ``required`` is supplied rather than authored twice"* — and **never** by the
    inference *"no binder call implies exempt."*

    **Why** :func:`_one_document`'s original reading could not see it. That
    route pairs an in-body class claim against an in-body plan source. ``cp-00``
    and ``s1-00`` assemble their lineage and construct their plan in the SAME
    body, so both readings land. ``examples/cp-04-corporate-family-tree``
    projects in ``produce.py::_project`` and assembles its
    :class:`~ccf.contracts.product.ProductLineage` in a sibling function, so
    :func:`_class_claim` answers ``None`` there — and the fail-closed default
    correctly refused it, because **an absent claim is not evidence of
    anything**. This route supplies the missing evidence positively rather than
    relaxing that default.

    **Three conditions, each a fact a TWO-document deployment would not
    exhibit:**

    1. The deployment registers **no** ``ccf.projection-requirements`` — checked
       by the caller, and it is the fact sabotage (a) inverts. A second
       operator-set document that can disagree is the binder's whole premise, so
       registering one withdraws the exemption and restores the demand. This is
       the same first reading :func:`_one_document` and
       :func:`_sdk_supplied_operator_set` each make.
    2. The one authored side **exists and is readable**
       (:func:`_config_declares_operator_set`): the config's reserved
       ``product_class`` section carries a non-empty operator set. A two-document
       deployment's plan reads the *requirements* artifact, not this.
    3. Every plan this body constructs reads its ``required=`` from **that
       declaration's own attribute** — at least one construction, and none from
       anywhere else. ``required=tuple(scenario.product_class.required_operator_keys)``
       is the shipped shape; ``required=tuple(scenario.operator_parameters)`` is
       `D-IMPL-137` **row C**, a second set authored where the Control Plane
       cannot see it, and row C stays red.

    Condition (3) reads :func:`_constructed_plan_sources` rather than
    :func:`_plan_sources` for the reason that function exists: ``_project``'s
    construction is passed straight to the engine, and a construction that is
    never assigned is invisible to the binding-pair reader — *and its
    invisibility is not evidence of anything* either.

    **This is an absence of demand, not a licence**, exactly as `D-IMPL-137`'s
    routes are: :func:`_binder_collapses` property (1) stays unconditional, so a
    body claiming this route and calling the binder anyway over a plan built
    from the very claim it is about to be compared against is STILL refused for
    the tautology. :func:`test_a_cp_04_shaped_exempt_body_that_calls_the_binder_is_refused`
    watches that rather than asserting it.
    """
    if not _config_declares_operator_set(root):
        return False
    sources = _constructed_plan_sources(scope, plan_classes)
    if not sources:
        return False
    return all(
        source is not None
        and source[-1:] == (PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE,)
        for source in sources
    )


def _one_document(
    scope: ast.AST,
    path: pathlib.Path,
    bindings: dict[str, tuple[_Binding, ...]],
    plan_classes: frozenset[str] | None = None,
) -> bool:
    """Whether the binder demand's premise is false for this body (D-IMPL-137).

    **TWO shapes of one-document deployment reach this, and the registration
    reading gates both.** The reading below — an in-body class claim paired
    against an in-body plan source — is the shape ``cp-00`` and ``s1-00`` ship.
    :func:`_supplied_by_the_product_class` is the second, ruled by `D-IMPL-234`
    for ``cp-04``, where the lineage is assembled in a sibling function and the
    plan's ``required=`` is instead read straight off the one authored
    declaration. Both are positive readings and neither infers the exemption
    from an absence; the ``_registers_requirements`` refusal above applies to
    both, which is what sabotage (a) in `D-IMPL-234`'s contract inverts.

    **A conjunction of two independent readings, and every other combination is
    refused.** The artifact tree says whether a second document is registered;
    the AST says whether the code actually reads one source. Row C — no
    registration, and a ``required=`` reading somewhere unrelated — means a
    second operator set was authored somewhere the Control Plane does not know
    about, and it stays red because this returns ``False`` and the demand
    applies unchanged.

    Fail-closed in three places, each deliberate: no artifact tree, no readable
    class claim, and no readable plan source. An absence of evidence is not the
    exemption; the exemption is claimable only by a deployment that HAS
    artifacts and demonstrably lacks that one. The first of the three is
    checked explicitly rather than folded into the registration read: a body
    with no artifact tree — a synthesized ``tmp_path`` fixture, most
    concretely — has ``_deployment_root`` return ``None``, and
    ``_registers_requirements(None)`` also answers ``False``, so a body with
    no artifact tree and one that HAS a tree but demonstrably lacks the
    registration would collapse into the same answer if this only tested the
    registration call's result. That collapse is exactly the gap it must not
    have: a body with no artifact tree must never reach the AST checks below,
    no matter what they would say, because it has made no claim to have
    checked anything against a Control Plane at all.
    """
    root = _deployment_root(path)
    if root is None or _registers_requirements(root):
        return False
    if _supplied_by_the_product_class(scope, path, root, plan_classes):
        return True
    claim = _class_claim(scope, bindings)
    if claim is None:
        return False
    sources = list(_plan_sources(scope, bindings, plan_classes).values())
    if not sources or any(source is None for source in sources):
        return False
    return all(_shares_a_source(claim, source) for source in sources)


# --- the SECOND way the premise can be false: the SDK supplies the set --------
#
# `D-IMPL-141` (Dave, 2026-08-16) changed the shape a deployment ships. Under
# the shape `_one_document` was written for, a deployment's own spine computed
# `required=` and could therefore be caught reading the product class's claim.
# Under the shape that ships now, the deployment writes ONE Python module — its
# projection — and `~ccf.products.resolver.build_governed_resolver` hands that
# module its operator set as a PARAMETER, already derived from the registered
# product class. There is no in-body read for `_class_claim` to find, and the
# construction is typically `return Plan(required=required, ...)` rather than an
# assignment, so `_plan_sources` records nothing either. Both fail-closed
# branches fire and the demand applies to a body that cannot satisfy it.
#
# It cannot satisfy it, and that is the finding rather than an inconvenience:
# adding the binder call here would hand `refuse_operator_set_divergence` the
# SDK-derived set on BOTH sides, which is exactly the tautology
# `_binder_collapses` property (1) refuses. The coverage assertion would be
# demanding a call the collapse assertion rejects.
#
# The real comparison did not disappear; it moved. For a `D-IMPL-136`
# single-file deployment it runs at boot, in
# `~ccf.deployment.config.derive_deployment`, which calls
# `~ccf.deployment.config._refuse_operator_set_divergence` over the product
# class's `required_operator_keys` and the `operators:` section's own keys.


#: The keyword :class:`~ccf.products.resolver.ProjectionPlanFactoryProtocol`
#: hands the operator set through, which is also the constructor keyword the
#: plan is then built with. They coincide by the Protocol's own signature rather
#: than by convention, and
#: :func:`test_the_factory_seam_still_names_its_operator_set_parameter` refuses
#: to let that coincidence rot into an assumption.
FACTORY_REQUIRED_PARAMETER = PLAN_REQUIRED_KEYWORD


def _scope_parameters(scope: ast.AST) -> frozenset[str]:
    """Every parameter name ``scope`` declares. Empty for a non-function body.

    Positional-only, ordinary and keyword-only alike: the seam is keyword-only
    today, and a gate that read only ``args.args`` would answer ``False`` for
    the very shape it exists to recognise.
    """
    if not isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef):
        return frozenset()
    arguments = scope.args
    return frozenset(
        argument.arg
        for argument in (
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
        )
    )


def _binding_plan_reference(root: pathlib.Path) -> tuple[str, str] | None:
    """``binding.yaml``'s ``plan:``, as ``(module path, attribute)``.

    ``None`` where the deployment carries no binding document, where the
    document does not parse, or where ``plan:`` is absent or not
    ``<module>:<attribute>`` shaped. Every one of those is fail-closed for the
    same reason :func:`_one_document`'s three are: a deployment that has made no
    readable claim has not claimed anything.

    Parsed plainly rather than through
    :func:`~ccf.client.adapters.binding_document.load_binding_document`,
    deliberately. That loader validates the **whole** document, so a deployment
    with an unrelated authoring mistake would raise here and take this gate down
    with it — a gate that reports a wiring typo as a binder-coverage failure.
    Only the one key is read; its *name* still comes from the SDK.
    """
    document = root / BINDING_DOCUMENT_NAME
    if not document.is_file():
        return None
    try:
        parsed = yaml.safe_load(document.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    if not isinstance(parsed, dict):
        return None
    reference = parsed.get(REFERENCE_KEYS[0])
    if not isinstance(reference, str):
        return None
    module_path, separator, attribute = reference.partition(":")
    if not separator or not module_path.strip() or not attribute.strip():
        return None
    return module_path.strip(), attribute.strip()


def _constructed_plan_sources(
    scope: ast.AST, plan_classes: frozenset[str] | None = None
) -> tuple[tuple[str, ...] | None, ...]:
    """Where every plan construction in ``scope`` reads its ``required=``.

    The same question :func:`_plan_sources` answers, over a **wider** set of
    statement forms: that function only sees constructions that are *assigned*,
    because tripwire (2) needs to pair a binding with a later use. A factory
    whose whole body is ``return Plan(required=required, …)`` assigns nothing,
    so it is invisible there — and its invisibility is not evidence of anything.

    Built from the same primitives — :func:`_is_plan_construction`,
    :func:`_keyword`, :func:`_path` — rather than from a second idea of what a
    plan construction is, so the two functions cannot disagree about *what* they
    are looking at, only about which statement forms carry it.
    """
    sources: list[tuple[str, ...] | None] = []
    for node in _scope_nodes(scope):
        if not isinstance(node, ast.Call):
            continue
        if not _is_plan_construction(node, plan_classes):
            continue
        required = _keyword(node, PLAN_REQUIRED_KEYWORD)
        sources.append(None if required is None else _path(required))
    return tuple(sources)


def _resolver_owns_the_seam(
    scope: ast.FunctionDef | ast.AsyncFunctionDef,
    path: pathlib.Path,
    root: pathlib.Path,
) -> bool:
    """Condition 3 of :func:`_sdk_supplied_operator_set`, in EITHER of its shapes.

    `D-IMPL-301` (Dave, 2026-09-09): *"`D-IMPL-141` describes an architectural
    ownership condition, not one specific wiring mechanism. A deployment
    qualifies as SDK-supplied when the tree proves that `GovernedResolver` owns
    the plan-construction -> execution seam and supplies the operator set,
    whether that ownership is established through a Control Plane
    `binding.yaml` or through direct canonical `build_governed_resolver`
    adoption."*

    **The invariant is unchanged: there must be ONE authoritative operator
    set.** What is widened is only the detector's vocabulary, which knew a
    single way of establishing that authority because a single way existed when
    it was written.

    **Shape A — the declared binding, unchanged.** The deployment's
    ``binding.yaml`` names this module and this function through its single
    permitted ``plan:`` reference: the Control Plane saying, on disk, *the SDK
    reaches this function and constructs the resolver around it*.

    **Shape B — direct canonical adoption.** The module reaches
    :func:`~ccf.products.resolver.build_governed_resolver` or
    :class:`~ccf.products.resolver.GovernedResolver`, and this body executes no
    projection engine of its own. The resolver then invokes ``plan_factory``
    itself and hands it the registered class's operator set, so the SDK is the
    sole authority exactly as in shape A — established by the program rather
    than by a document.

    Both shapes are conjunctive with conditions 1, 2, 4 and 5, which are
    unchanged and do the rest of the work: no ``ccf.projection-requirements``
    registration, a ``required`` parameter on the factory, at least one
    constructed plan, and every constructed plan sourcing its operator set from
    that parameter. A body that authored a competing set still fails at 5
    whichever shape it takes.

    **No example is named here.** cp-05 qualifies under shape B because the
    tree says so, and any later adopter qualifies the same way without an edit.
    """
    reference = _binding_plan_reference(root)
    if reference is not None:
        module_path, attribute = reference
        if attribute == scope.name and (root / module_path).resolve() == path.resolve():
            return True
    return _delegates_the_seam_to_the_resolver(path, scope)


def _sdk_supplied_operator_set(
    scope: ast.AST,
    path: pathlib.Path,
    plan_classes: frozenset[str] | None = None,
) -> bool:
    """Whether the SDK — not this body — supplied the operator set.

    **Positively signalled, never inferred from absence.** Five conditions, and
    each one is a fact readable from the tree rather than a gap in it:

    1. The body sits in a deployment with a Control Plane authoring surface
       (:func:`_deployment_root`), so a synthesized ``tmp_path`` fixture is
       refused exactly as :func:`_one_document` refuses it.
    2. That deployment registers **no** ``ccf.projection-requirements``. If it
       registers one, a second operator set was authored and the demand stands
       unchanged — this is the same first reading :func:`_one_document` makes,
       and it is made here too rather than shared, because sharing it would
       make one route's answer depend on the other's.
    3. The deployment's ``binding.yaml`` names **this module and this function**
       through its single permitted ``plan:`` reference. This is the load-bearing
       condition: it is the Control Plane saying, on disk, *the SDK reaches this
       function and constructs the resolver around it*. A module the binding
       document does not name is a module the SDK never calls, and it gets no
       exemption.
    4. The function declares the seam's operator-set parameter.
    5. Every plan it constructs is built from **that parameter** — at least one
       construction, and no construction from anywhere else. A factory that
       builds its plan from some other source has authored a second operator set
       the Control Plane does not know about, which is `D-IMPL-137` row C, and
       row C stays red.

    **This is a different exemption from** :func:`_one_document`\\ **'s, and it
    is counted separately on purpose.** Row B is a deployment that authors one
    document where it could have authored two. This is a deployment that authors
    **none** — it has no operator set of its own to author. Folding the two
    together would let either roster absorb the other's growth, and each
    roster exists so that an *unruled* claimant is red and a human rules on it.
    :data:`RULED_SDK_SUPPLIED_DEPLOYMENTS` bounds this one.
    """
    root = _deployment_root(path)
    if root is None or _registers_requirements(root):
        return False
    if not isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef):
        return False

    if not _resolver_owns_the_seam(scope, path, root):
        return False

    if FACTORY_REQUIRED_PARAMETER not in _scope_parameters(scope):
        return False

    sources = _constructed_plan_sources(scope, plan_classes)
    if not sources:
        return False
    return all(
        _shares_a_source(source, (FACTORY_REQUIRED_PARAMETER,)) for source in sources
    )


def _premise_is_false(
    scope: ast.AST,
    path: pathlib.Path,
    bindings: dict[str, tuple[_Binding, ...]],
    plan_classes: frozenset[str] | None = None,
) -> bool:
    """Either route by which the binder demand has nothing to demand.

    One predicate rather than two conditions spelled at each call site, for the
    reason :func:`_exemption_problems` gives for its own existence: the demand
    site, the collapse properties and their controls must judge by the same
    code, or a third route added later reaches one of them and not the others.

    The two ceilings stay separate behind it —
    :func:`_one_document_deployments` and :func:`_sdk_supplied_deployments` each
    read their own route — so this union bounds nothing and is not asked to.
    """
    return _one_document(scope, path, bindings, plan_classes) or (
        _sdk_supplied_operator_set(scope, path, plan_classes)
    )


# --- tripwire (1): both gate arguments from one source ------------------------


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _callee(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _gate_collapses(scope: ast.AST, path: pathlib.Path) -> list[str]:
    """Every same-source pairing of Gate 2's two arguments in one body."""
    bindings = _bindings(scope)
    gate_sides: list[tuple[int, tuple[str, ...] | None]] = []
    lineage_sides: list[tuple[int, tuple[str, ...] | None]] = []

    for node in _scope_nodes(scope):
        if not isinstance(node, ast.Call):
            continue
        callee = _callee(node)
        if callee == GATE_CALL:
            argument = _keyword(node, GATE_RESOLVED_KEYWORD)
            if argument is not None:
                gate_sides.append(
                    (
                        node.lineno,
                        _resolve_at(_path(argument), _at(argument), bindings),
                    )
                )
        elif callee == LINEAGE_CONSTRUCTOR:
            argument = _keyword(node, LINEAGE_DECLARED_KEYWORD)
            if argument is not None:
                lineage_sides.append(
                    (
                        node.lineno,
                        _resolve_at(_path(argument), _at(argument), bindings),
                    )
                )

    problems: list[str] = []
    for gate_line, resolved in gate_sides:
        for lineage_line, declared in lineage_sides:
            if not _shares_a_source(resolved, declared):
                continue
            assert resolved is not None and declared is not None
            problems.append(
                f"{path.relative_to(REPO_ROOT)}:{gate_line}:"
                f" `{GATE_CALL}(..., {GATE_RESOLVED_KEYWORD}=...)` and the"
                f" `{LINEAGE_CONSTRUCTOR}(...)` at line {lineage_line} both"
                f" read `{_render(declared)}`."
                " Gate 2 (lineage strict equality, whitepaper §7.6,"
                " INV-CH7-47) then compares a value against itself: it cannot"
                " fail, it stays green, and the invariant is gone with nothing"
                " failing to say so. This is the shape CR-2 found at nine call"
                " sites. Fill the product's lineage from the product-class"
                " DECLARATION — `frozenset(declared.required_operator_keys)` —"
                " and leave `engine_resolved` as the engine's own value"
                " (design E2, D-IMPL-86 element (1))."
            )
    return problems


def _gate_scopes() -> list[tuple[pathlib.Path, ast.AST]]:
    """Every lexical body under the scanned trees that calls ``run_gates``."""
    found: list[tuple[pathlib.Path, ast.AST]] = []
    for path in _python_sources(SCANNED_TREES):
        tree = _parse(path)
        if tree is None:
            continue
        for scope in _scopes(tree):
            for node in _scope_nodes(scope):
                if isinstance(node, ast.Call) and _callee(node) == GATE_CALL:
                    found.append((path, scope))
                    break
    return found


def test_the_scan_root_membership_is_exactly_the_expected_sets() -> None:
    """The three floors in this module cannot see a root SWAP. This can.

    ``23-RESEARCH.md`` finding **S-16**. All three counts below —
    :data:`MINIMUM_GATE_CALL_SITES`, :data:`MINIMUM_PROJECTING_BODIES` and
    :data:`MINIMUM_RESOLVED_BINDER_SITES` — are floors, and a floor asserts a
    total, not a source. After Phase 23's move,
    ``BINDER_SCANNED_TREES = ("archive",)`` alone keeps all of them green on
    the identical witnesses while the surviving ``examples/`` trees stop being
    scanned entirely. Nothing else in this module would say so.

    Asserted by set equality, not by ``in`` checks. An ``in`` check passes over
    a tuple that has grown, and growth is how a tree joins a scan nobody
    reviewed.

    ``archive`` was added in plan ``23-03`` *before* the move, so the widening
    could be proven a strict no-op against a tree where ``archive/`` did not
    yet exist. **No floor constant was touched.** Widening the root preserves
    every count exactly — the same witnesses are found at the new path — and
    :func:`test_the_binder_scan_is_not_vacuous` says why lowering one instead
    is the fix that loses the coverage.
    """
    assert set(SCANNED_TREES) == {"src", "runtime", "examples", "archive"}, (
        "the gate-call scan roots changed. `tests/` stays out for the reason"
        " the module docstring gives; `examples` and `archive` must BOTH be in,"
        " because after the move the witnesses are split across the two and a"
        " count cannot tell which side it read them from."
    )
    assert set(BINDER_SCANNED_TREES) == {"examples", "archive"}, (
        "the binder-coverage scan roots changed. This is the tightest of the"
        " three floors and the one S-16 names: `('archive',)` alone keeps"
        " 14/12 green on renamed witnesses while every surviving example stops"
        " being scanned."
    )
    for name, trees in (
        ("SCANNED_TREES", SCANNED_TREES),
        ("BINDER_SCANNED_TREES", BINDER_SCANNED_TREES),
    ):
        assert "examples" in trees, f"{name} lost the live examples tree"
        assert "archive" in trees, f"{name} lost the archive"


def test_the_gate_scan_is_not_vacuous() -> None:
    """A tripwire that matched zero call sites would pass forever."""
    found = _gate_scopes()
    assert len(found) >= MINIMUM_GATE_CALL_SITES, (
        f"{len(found)} `{GATE_CALL}` call sites found,"
        f" {MINIMUM_GATE_CALL_SITES} expected. {FLOOR_REMOVAL_INSTRUCTION} Found:"
        + str(
            [
                f"{path.relative_to(REPO_ROOT)}:{_scope_line(scope)}"
                for path, scope in found
            ]
        )
    )


@pytest.mark.parametrize(
    ("path", "scope"),
    _gate_scopes(),
    ids=lambda value: (
        str(value.relative_to(REPO_ROOT)) if isinstance(value, pathlib.Path) else ""
    ),
)
def test_no_call_site_fills_both_gate_arguments_from_one_source(
    path: pathlib.Path, scope: ast.AST
) -> None:
    """D-IMPL-86 element (5), closed structurally rather than site by site."""
    problems = _gate_collapses(scope, path)
    assert not problems, "\n".join(problems)


def test_the_tripwire_detects_the_shape_it_exists_to_refuse() -> None:
    """The tripwire is watched to fire, and watched to stay quiet.

    Both halves, for the reason
    ``test_gate_independence.py::test_perturbing_engine_resolved_is_refused_and_the_declared_set_is_not``
    gives: a check that always fires and a check that never fires each pass one
    half, and only the pair says the comparison is live.

    The probe bodies are **assembled** at runtime rather than written out, so
    this module's own source is not what a scan trips over — the discipline
    ``test_required_operators_guard.py::test_the_guard_detects_the_shortcut_it_exists_to_refuse``
    and ``tests/examples/test_surface_audit.py`` both use. The check itself
    matches
    ``ast`` nodes, never text, so the assembly is belt-and-braces rather than
    load-bearing.
    """
    engine = ".".join(("execution", LINEAGE_DECLARED_KEYWORD))
    gate = f"{GATE_CALL}(candidate, {GATE_RESOLVED_KEYWORD}="
    lineage = f"{LINEAGE_CONSTRUCTOR}({LINEAGE_DECLARED_KEYWORD}="

    caught = (
        # the direct same-name case — the shape CR-2 found at all nine sites
        "def serve(execution, candidate):\n"
        f"    product = {lineage}{engine})\n"
        f"    return {gate}{engine})\n",
        # one alias hop, on both sides
        "def serve(execution, candidate):\n"
        f"    resolved = {engine}\n"
        f"    product = {lineage}resolved)\n"
        f"    return {gate}resolved)\n",
        # a chain of aliases — the fixed point, not just the first hop
        "def serve(execution, candidate):\n"
        f"    a = {engine}\n"
        "    b = a\n"
        f"    product = {lineage}a)\n"
        f"    return {gate}b)\n",
        # the walrus spelling, wrapped in a transparent set conversion
        "def serve(execution, candidate):\n"
        f"    product = {lineage}frozenset(resolved := {engine}))\n"
        f"    return {gate}resolved)\n",
        # the attribute chain, with a `cast` in the way on one side
        "def serve(execution, candidate):\n"
        f"    product = {lineage}cast(frozenset, {engine}))\n"
        f"    return {gate}{engine})\n",
        # WR-F4 — the identical METHOD call on both sides. One expression, one
        # value, and Gate 2 comparing it against itself. WR-02 was right that
        # collapsing a call to its bare receiver was red on correct code, and
        # its fix — dropping the call to `None` — admitted this. Both are
        # avoidable: the path keeps the member name, so this is caught and the
        # two benign method probes below stay quiet.
        "def serve(execution, candidate):\n"
        f"    product = {lineage}execution.resolved())\n"
        f"    return {gate}execution.resolved())\n",
        # the same, one alias hop apart — the binding is the source, so both
        # reads of it are one source
        "def serve(execution, candidate):\n"
        "    ops = execution.resolved()\n"
        f"    product = {lineage}ops)\n"
        f"    return {gate}ops)\n",
        # and where the value is out of reach entirely, the BINDING is still
        # the source: two reads of one unreadable local are one value
        "def serve(execution, candidate):\n"
        "    ops = derive(execution)\n"
        f"    product = {lineage}ops)\n"
        f"    return {gate}ops)\n",
    )
    for source in caught:
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert _gate_collapses(function, REPO_ROOT / "probe.py"), source

    benign = (
        # the compliant post-E2 shape: the claim from the product class, the
        # resolution from the engine — the two documents design E2 separates
        "def serve(execution, candidate, declared):\n"
        f"    product = {lineage}"
        "frozenset(declared.required_operator_keys))\n"
        f"    return {gate}{engine})\n",
        # two attributes of one object are two values, not one
        "def serve(self, candidate):\n"
        f"    product = {lineage}self._declared)\n"
        f"    return {gate}self._resolved)\n",
        # a METHOD on one object and an attribute of it are likewise two
        # members, and the module cannot see what the method returns. Reading
        # `self.declared_claim()` off its receiver as `self` collapsed it
        # against `self._resolved` and made this correct body red — the same
        # `self` collapse the two-attribute probe above exists to prevent,
        # arriving through the call node instead of the attribute node.
        "def serve(self, candidate):\n"
        f"    product = {lineage}self.declared_claim())\n"
        f"    return {gate}self._resolved)\n",
        # and the same for two accessors on one artifact object, which is an
        # ordinary refactor of the compliant pattern rather than an exotic one
        "def serve(product_class, candidate):\n"
        f"    product = {lineage}product_class.claim())\n"
        f"    return {gate}product_class.resolved_ops)\n",
        # the replay leg: the lineage rehydrated from the replay record
        "def rehydrate(execution, candidate, record):\n"
        f"    product = {lineage}"
        "frozenset(record.content_generation_path.operator_plan))\n"
        f"    return {gate}{engine})\n",
        # WR-F2 — reusing a local name for two different values is ordinary
        # Python, and the two values are two sources. This is the compliant
        # design-E2 body: the lineage from the product-class declaration, the
        # gate's side from the engine. Recording one binding per NAME, over a
        # traversal that yields statements in reverse, made both sides resolve
        # to the second assignment and reported this correct body as a collapse.
        "def serve(execution, candidate, declared):\n"
        f"    ops = frozenset(declared.required_operator_keys)\n"
        f"    product = {lineage}ops)\n"
        f"    ops = {engine}\n"
        f"    return {gate}ops)\n",
        # the same for two unreadable bindings: `derive(execution)` and
        # `derive(candidate)` are two evaluations and two values, and the line
        # of the binding is what tells them apart
        "def serve(execution, candidate):\n"
        "    ops = derive(execution)\n"
        f"    product = {lineage}ops)\n"
        "    ops = derive(candidate)\n"
        f"    return {gate}ops)\n",
        # two DIFFERENT methods on one receiver are two members and two
        # sources, exactly as two attributes are — the path keeps the member
        # name, so restoring the method-call reading does not restore WR-02
        "def serve(self, candidate):\n"
        f"    product = {lineage}self.declared_claim())\n"
        f"    return {gate}self.resolved_ops())\n",
    )
    for source in benign:
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _gate_collapses(function, REPO_ROOT / "probe.py"), source


def test_the_tripwire_does_not_pair_across_two_bodies() -> None:
    """One body means one body.

    A ``ProductLineage`` built in one method and a ``run_gates`` call in
    another are not the collapse — they may be two entirely unrelated products.
    A check using ``ast.walk`` from the class node would report them as one, and
    would be red on correct code.
    """
    engine = ".".join(("execution", LINEAGE_DECLARED_KEYWORD))
    source = (
        "class Deployment:\n"
        f"    def build(self, execution):\n"
        f"        return {LINEAGE_CONSTRUCTOR}"
        f"({LINEAGE_DECLARED_KEYWORD}={engine})\n"
        f"    def gate(self, execution, candidate):\n"
        f"        return {GATE_CALL}"
        f"(candidate, {GATE_RESOLVED_KEYWORD}={engine})\n"
    )
    tree = ast.parse(source)
    for scope in _scopes(tree):
        assert not _gate_collapses(scope, REPO_ROOT / "probe.py"), _scope_label(
            scope
        )


# --- tripwire (2): every projecting body names the binder ---------------------


def _plan_classes_in(tree: ast.Module) -> frozenset[str]:
    """Classes in one module that satisfy ``ProjectionPlan`` structurally.

    ``src/ccf/projection/plan.py``'s own words: *"Any type exposing
    ``required_operators()`` and ``invoke()`` is a projection."* This reads
    exactly that, off the class body, and asks nothing about the name.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        members = {
            member.name
            for member in node.body
            if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        if PLAN_PROTOCOL_MEMBERS <= members:
            found.add(node.name)
    return frozenset(found)


_TREE_PLAN_CLASSES: frozenset[str] | None = None


def _plan_classes() -> frozenset[str]:
    """Every structurally-conforming plan class name in the scanned trees."""
    global _TREE_PLAN_CLASSES  # noqa: PLW0603 - a one-shot scan of the tree
    if _TREE_PLAN_CLASSES is None:
        found: set[str] = set()
        for path in _python_sources(SCANNED_TREES):
            tree = _parse(path)
            if tree is not None:
                found |= _plan_classes_in(tree)
        _TREE_PLAN_CLASSES = frozenset(found)
    return _TREE_PLAN_CLASSES


def _is_plan_construction(
    node: ast.AST, plan_classes: frozenset[str] | None = None
) -> bool:
    """A projection plan being built — recognised without reading its name.

    **This is the CR-F1 fix, and the ordering of the branches is the finding.**
    The predecessor required the class name to end in ``Plan``. But
    ``ProjectionPlan`` is a :class:`typing.Protocol` whose docstring commits to
    the opposite — *"Structural, not nominal … There is no base class to inherit
    and no registry decorator to remember"* — so renaming one identifier made
    property (1), the entire substance of the CR-03 fix, silently vacuous while
    coverage, properties (2) and (3) and all three floors stayed green. A check
    that keys on a naming convention against a type the SDK is deliberately
    structural about is a check that can be renamed away.

    Three branches. The first two are name-independent and are what the check
    now rests on:

    1. **The callee names a class that satisfies the Protocol structurally** —
       its body defines both :data:`PLAN_PROTOCOL_MEMBERS`. This is the SDK's
       own definition of "is a projection", applied to the class the call
       constructs. Renaming ``QuickstartPlan`` to ``CreditProjection`` renames
       its ``class`` statement too, so this branch follows the rename.
    2. **The call passes both ``plan_id=`` and ``required=``** — the constructor
       shape every plan in the suite has, and the two keywords the checks
       actually read. This catches a plan class whose *definition* is out of
       reach: imported from a package, or from a tree this module does not scan.

    3. The ``*Plan`` suffix together with ``required=`` is the pre-CR-F1 rule.
       It is kept, and it earns its keep on exactly one case: a plan class
       defined outside the scanned trees *and* constructed without ``plan_id=``.
       Dropping it would narrow the check, and narrowing is not what this fix
       is for. It is no longer load-bearing — measured over ``src/``,
       ``runtime/``, ``examples/`` and ``tests/``, every one of its **fourteen**
       matches is also matched by **branch 2**; branch 1 matches eleven of them,
       because the other three are defined in ``tests/``, which
       :func:`_plan_classes` does not scan — which is itself the case branch 2
       exists to cover. So branch 3 is redundant *with branch 2*, not with branch
       1, and it must not be read as load-bearing, which is why it is listed last
       and named a net.

    **The false-positive cost was measured rather than assumed**, because a
    check red on correct code is the defect this cycle keeps producing. Counts
    over ``src/``, ``runtime/``, ``examples/`` and ``tests/``, driving the
    shipped predicate:

    ===================================================  =====
    branch 1, over the index this module actually builds     11
    branch 2 (``plan_id=`` and ``required=``)                14
    branch 3 (``*Plan`` and ``required=``)                   14
    the union — what this function answers                   14
    ``required=`` alone                                      67
    ===================================================  =====

    All fourteen construct a class defining both Protocol members, so there are
    **zero** non-plan constructions in the union. Branch 1's eleven are the calls
    whose class is defined in ``src/``, ``runtime/`` or ``examples/``; an index
    built over ``tests/`` as well would match thirty-five, and that wider index
    is a probe rather than something the shipped code runs — the number belongs
    to a scan this module does not perform, and stating it as branch 1's was
    WR-01. Under ``ProjectionPlan``'s own structural commitment a class defining
    both members *is* a projection, so branch 1 has no false positive it is
    possible to state.

    Inside ``examples/``, the tree this tripwire scans, all three branches select
    the identical eleven bodies the suffix rule selected, so nothing became red
    that was green. The reviewer's proposed rekey — ``required=`` **alone** — was
    measured too and rejected: it matches sixty-seven calls, **fifty-three** of
    them ``argparse`` (``add_argument`` 28, ``add_subparsers`` 10), ``_policy``
    (9), ``basic_debt`` (5) and ``JSONSchema`` (1). One of the fifty-three is
    inside ``examples/`` — ``03-harness-portability/run.py``'s own ``main()`` —
    which the rekey would turn into a projecting body obliged to call the binder.

    **A walrus is unwrapped first** (:func:`_unwrap`). ``(plan := FooPlan(...))``
    *is* the construction it evaluates to, and answering ``False`` for it routed
    the shape past property (2)'s hoist branch and past
    :func:`_handed_plan_source`'s inline branch at once — R4-WR-02, and the reason
    the ledger's "a plan constructed inline as ``execute``'s ``plan=``" row was
    true only of the spelling without the walrus.
    """
    if isinstance(node, ast.NamedExpr):
        node = _unwrap(node)
    if not isinstance(node, ast.Call):
        return False
    callee = _callee(node)
    if callee is None:
        return False
    if callee in (_plan_classes() if plan_classes is None else plan_classes):
        return True
    keywords = {keyword.arg for keyword in node.keywords}
    if {PLAN_ID_KEYWORD, PLAN_REQUIRED_KEYWORD} <= keywords:
        return True
    return callee.endswith(PLAN_CLASS_SUFFIX) and PLAN_REQUIRED_KEYWORD in keywords


def _is_plan_execution(node: ast.AST) -> bool:
    """A projection being run: ``....execute(plan=..., ...)``.

    The ``plan`` keyword is what separates a projection execution from a
    workflow one — ``engine.execute(workflow, execution_id=...)`` in examples
    05 and 06 runs no projection and must not be swept in.
    """
    if not isinstance(node, ast.Call):
        return False
    if _callee(node) != ENGINE_EXECUTE_METHOD:
        return False
    return any(keyword.arg == ENGINE_PLAN_KEYWORD for keyword in node.keywords)


def _names_the_binder(scope: ast.AST) -> bool:
    """The binder appears in this body. **Naming only** — see below.

    This is the coverage half of tripwire (2) and it is deliberately kept as a
    separate, weaker predicate from :func:`_binder_collapses`, which is the
    half that reads the call's arguments. Coverage answers "is the binder
    here"; the argument checks answer "is it doing anything". CR-03 was the
    finding that the first had been mistaken for the second.
    """
    for node in _scope_nodes(scope):
        if isinstance(node, ast.Call) and _callee(node) == BINDER_CALL:
            return True
    return False


def _bound_object(
    argument: ast.expr, bindings: dict[str, tuple[_Binding, ...]]
) -> tuple[str, ...] | None:
    """Which **object** a ``plan=`` argument names, as a source token.

    Ordinarily :func:`_binding_path` resolved at the read's position, which is
    the question "which object is this name". A walrus is the one spelling where
    the expression both *is* an object and *binds* one, and the two answers must
    agree: ``binder(plan=(plan := FooPlan(...)))`` hands the binder the object
    the walrus just bound, so the token is that binding's own — the same token
    :func:`_plan_sources` keys the construction under, taken from the same
    ``_Binding`` so the two cannot drift.

    Resolving it to ``None`` instead was red on correct code: the binder was
    handed the very object the engine went on to run, and property (2) reported
    the execution as unbound because the two sides had no token in common. That
    is the direction R4-WR-02's *other* half runs in — the walrus made the module
    silent at the execution seam and wrong at the binder seam, from one omission.
    """
    if isinstance(argument, ast.NamedExpr):
        binding = dict(_binding_records(argument)).get(argument.target.id)
        if binding is not None:
            return (_opaque(argument.target.id, binding.position),)
    return _resolve_at(_binding_path(argument), _at(argument), bindings)


class _BinderCall(NamedTuple):
    """One ``refuse_operator_set_divergence`` call, with both sides resolved.

    ``position`` is ``(line, column)`` because property (3) — the binder
    precedes the engine — is an *ordering* question, and a line number cannot
    order ``plan = P(); bind(plan=plan); run(plan=plan)``, which is correct code
    a line-ordered comparison reported red at two properties at once.
    """

    position: tuple[int, int]
    declared: tuple[str, ...] | None
    handed: tuple[str, ...] | None
    plan_node: ast.expr | None

    @property
    def lineno(self) -> int:
        """The line ``position`` falls on — for failure messages."""
        return self.position[0]


def _plan_sources(
    scope: ast.AST,
    bindings: dict[str, tuple[_Binding, ...]],
    plan_classes: frozenset[str] | None = None,
) -> dict[tuple[str, ...], tuple[str, ...] | None]:
    """Each plan construction, and where the ``required=`` it was built from reads.

    ``plan = QuickstartPlan(plan_id=…, required=requirements.required_operator_keys)``
    ending at line 231 column 84 binds the source token ``plan@231:84`` to
    ``("requirements", "required_operator_keys")``. That mapping is the whole
    basis of the tautology check: the binder is handed ``plan``, and this says
    which of the two authored documents ``plan`` was built from.

    **Keyed by the binding, not by the name** (WR-F2). Its predecessor keyed on
    the name alone with ``setdefault`` over a reverse-order traversal, so a body
    that constructs one plan, binds it, executes it, and then rebinds ``plan``
    to a second construction had *one* entry for the two — and property (2),
    matching on names, reported the second execution as bound by the first
    call's binder, which never saw that object. :func:`_opaque` gives each
    construction its own token and :func:`_resolve_at` resolves a use to the
    construction in force at that position, so the two are two.

    **The token is taken from the same record the resolver reads.** Each
    construction's key is built from :func:`_binding_records`'s own ``_Binding``
    for that target rather than from the statement's line, so the key here and
    the key :func:`_resolve_at` synthesises cannot drift apart — which they
    would the moment a binding's effective position stopped being its
    statement's start, as :func:`_after` makes it.
    """
    sources: dict[tuple[str, ...], tuple[str, ...] | None] = {}
    for node in _scope_nodes(scope):
        targets, value = _assignment(node)
        if value is None or not _is_plan_construction(value, plan_classes):
            continue
        construction = _unwrap(value)
        assert isinstance(construction, ast.Call)
        required = _keyword(construction, PLAN_REQUIRED_KEYWORD)
        source = (
            None
            if required is None
            else _resolve_at(_path(required), _at(required), bindings)
        )
        records = dict(_binding_records(node))
        for target in targets:
            binding = records.get(target)
            if binding is None:
                continue
            sources.setdefault((_opaque(target, binding.position),), source)
    return sources


def _binder_calls(
    scope: ast.AST, bindings: dict[str, tuple[_Binding, ...]]
) -> list[_BinderCall]:
    calls: list[_BinderCall] = []
    for node in _scope_nodes(scope):
        if not (isinstance(node, ast.Call) and _callee(node) == BINDER_CALL):
            continue
        declared_arg = _keyword(node, BINDER_DECLARED_KEYWORD)
        plan_arg = _keyword(node, BINDER_PLAN_KEYWORD)
        calls.append(
            _BinderCall(
                position=_at(node),
                declared=(
                    None
                    if declared_arg is None
                    else _resolve_at(
                        _path(declared_arg), _at(declared_arg), bindings
                    )
                ),
                # `_bound_object`, not `_path`: `plan=` names an OBJECT, and the
                # question property (2) asks is which one. A call spelled here
                # is a fresh object no binder can have been handed, and the
                # inline branches below say so rather than resolving it.
                handed=(
                    None if plan_arg is None else _bound_object(plan_arg, bindings)
                ),
                plan_node=plan_arg,
            )
        )
    return calls


class _Execution(NamedTuple):
    """One ``ProjectionEngine(...).execute(plan=…)`` and the plan it runs.

    ``position`` for the same reason :class:`_BinderCall` carries one: property
    (2) asks whether a binder call precedes *this* execution, and on one
    physical line only a column can answer.
    """

    position: tuple[int, int]
    plan: tuple[str, ...] | None
    plan_node: ast.expr | None

    @property
    def lineno(self) -> int:
        """The line ``position`` falls on — for failure messages."""
        return self.position[0]


def _executions(
    scope: ast.AST, bindings: dict[str, tuple[_Binding, ...]]
) -> list[_Execution]:
    found: list[_Execution] = []
    for node in _scope_nodes(scope):
        if not _is_plan_execution(node):
            continue
        assert isinstance(node, ast.Call)
        argument = _keyword(node, ENGINE_PLAN_KEYWORD)
        found.append(
            _Execution(
                position=_at(node),
                plan=(
                    None if argument is None else _bound_object(argument, bindings)
                ),
                plan_node=argument,
            )
        )
    return found


def _handed_plan_source(
    call: _BinderCall,
    sources: dict[tuple[str, ...], tuple[str, ...] | None],
    bindings: dict[str, tuple[_Binding, ...]],
    plan_classes: frozenset[str] | None = None,
) -> tuple[str, ...] | None:
    """Where the ``required=`` of the plan handed to ``call`` reads, if readable."""
    if call.plan_node is not None and _is_plan_construction(
        call.plan_node, plan_classes
    ):
        # `binder(declared=…, plan=FooPlan(required=…))` — inline, read directly.
        # `_unwrap` because `plan=(p := FooPlan(required=…))` is the same call
        # with a walrus around it (R4-WR-02).
        construction = _unwrap(call.plan_node)
        assert isinstance(construction, ast.Call)
        required = _keyword(construction, PLAN_REQUIRED_KEYWORD)
        return (
            None
            if required is None
            else _resolve_at(_path(required), _at(required), bindings)
        )
    if call.handed is None:
        return None
    return sources.get(call.handed)


def _binder_collapses(
    scope: ast.AST,
    path: pathlib.Path,
    plan_classes: frozenset[str] | None = None,
) -> list[str]:
    """The binder is *doing something* in this body, not merely spelled in it.

    Three properties, each of which a body naming the binder can violate while
    the coverage predicate stays green — which is what CR-03 found:

    1. **The binder's two arguments are two documents.** A plan built as
       ``required=declared.required_operator_keys`` and then handed to the
       binder alongside that same ``declared`` makes ``claimed == required``
       hold unconditionally at ``refuse_operator_set_divergence``'s
       comparison. The binder is green, it
       *cannot* fail, and ``ccf.projection-requirements`` has been routed
       around. This is CR-2's shape moved one seam upstream.
    2. **The plan bound is the plan run.** A binder handed one plan while the
       engine executes another checks a plan nothing assembles a product from.
    3. **The binder precedes the engine.** D-IMPL-86's correction places the
       call *between* plan construction and
       :meth:`~ccf.projection.engine.ProjectionEngine.execute`; a call after
       ``execute`` runs when a product has already been assembled from a set
       the deployment's own claim may contradict.

    **What "precedes" means here, and what it does not.** Properties (2) and (3)
    compare source **positions** — ``(line, column)`` — which is evaluation
    order for statements and for the top-level argument expressions this module
    reads, and which is why the whole compliant body written on one physical
    line is admitted where a line comparison reported it red at both properties
    at once. It is *not* execution order: a binder call inside a never-taken
    branch precedes the engine and never runs (reachability, named in the module
    docstring), and a loop makes lines run out of source order in both
    directions (R4-WR-03, likewise named). Neither is readable from a
    single-pass AST walk over one body, and this function does not claim to see
    them.

    **This does not close the authorship residual (R-3), and must not be read
    as doing so.** R-3 is the *authoring* boundary — an author copying one YAML
    document's keys into the other — and D-IMPL-86 establishes it as
    AST-undetectable *in principle*, because the compliant and the violating
    artifact are textually identical. What is checked here is **code**:
    ``required=declared.required_operator_keys`` is an identifier path this
    module already resolves, so it is detectable and now detected. The two
    remain separate findings and R-3 remains open.

    **A body with no binder call at all is reported here as well as by the
    coverage assertion, and that is deliberate** (IN-03) — *for a body the
    demand applies to*.
    :func:`test_every_bound_body_has_a_readable_plan_source` takes an early exit
    for such a body and its docstring gives the reason as "reporting it twice
    would tell one story in two voices" — but the operative reason there is
    narrower than that phrasing: with no calls, *its* message ("every call was
    handed a plan whose ``required=`` cannot be read") is **vacuous**, naming no
    line and describing nothing. Property (3)'s message on the same body — "a
    projection is executed here with no binder call before it" — is **true**, is
    specific, and names the executing line. A true, specific second report costs
    a contributor nothing (one edit fixes both) and a vacuous one costs them a
    wrong lead, which is why the two assertions behave differently here.

    **That double report does not hold for an exempt body, and the paragraph
    above was unqualified until D-IMPL-137.** Where ``demanded`` is false the
    ``if demanded:`` guards switch property (3) off, and
    :func:`test_every_projecting_example_body_names_the_binder` takes its own
    early return, so a one-document body with no binder call is reported by
    **neither** — which is the ruling working rather than a gap in it: there is
    no demand for either report to be made against. What still fires on such a
    body is property (1), and only if it calls the binder anyway. The
    qualification is recorded here rather than folded silently into the
    sentences above, because the unqualified reading was true of this module
    for four review rounds and a reader comparing revisions should be able to
    see which way it moved.
    """
    bindings = _bindings(scope)
    sources = _plan_sources(scope, bindings, plan_classes)
    calls = _binder_calls(scope, bindings)
    executions = _executions(scope, bindings)
    where = path.relative_to(REPO_ROOT)
    problems: list[str] = []

    # D-IMPL-137: properties (2) and (3) ask whether the binder was called on
    # the right object at the right time. Where the deployment authors ONE
    # operator-set document there is no second operand for the binder to
    # compare, so there is no call for them to ask about — and property (2),
    # spelled as `any(... for call in calls)`, would otherwise fire on every
    # execution merely because `calls` is empty. Property (1) stays
    # unconditional: a body that calls the binder anyway is still refused for
    # the tautology, which is what makes this an absence of demand rather than
    # a licence.
    # Both routes, through `_premise_is_false`: row B (the deployment authored
    # one document) and the `D-IMPL-141` shape (the SDK supplied the set, so the
    # deployment authored none). Property (1) stays unconditional under either.
    demanded = not _premise_is_false(scope, path, bindings, plan_classes)

    # (1) the binder's two sides must be two documents
    for call in calls:
        required = _handed_plan_source(call, sources, bindings, plan_classes)
        if not _shares_a_source(call.declared, required):
            continue
        assert call.declared is not None and required is not None
        problems.append(
            f"{where}:{call.lineno}: the plan handed to `{BINDER_CALL}` reads"
            f" its `{PLAN_REQUIRED_KEYWORD}=` from `{_render(required)}`, which"
            f" is the same source as `{BINDER_DECLARED_KEYWORD}="
            f"{_render(call.declared)}`. The binder then compares a value"
            " against itself: it cannot fail, it stays green, and the"
            " `ccf.projection-requirements` artifact has been routed around"
            " entirely. This is CR-2's shape at the binder seam. Build the"
            f" plan's `{PLAN_REQUIRED_KEYWORD}=` from the projection's OWN"
            " document — `requirements.required_operator_keys` — and leave"
            f" `{BINDER_DECLARED_KEYWORD}=` as the product class's claim"
            " (design E2, D-IMPL-86)."
        )

    # (3) ordering, for the case (2) cannot read. Positions and not lines: a
    # `plan = P(); bind(plan=plan); run(plan=plan)` written on one physical line
    # is correct code that a line comparison reported red here and at (2).
    if demanded:
        first_position = min(
            (execution.position for execution in executions), default=None
        )
        if first_position is not None and not any(
            call.position < first_position for call in calls
        ):
            first_execution = first_position[0]
            problems.append(
                f"{where}:{first_execution}: a projection is executed here with"
                f" no `{BINDER_CALL}` call before it. The binder belongs BETWEEN"
                " plan construction and `ProjectionEngine.execute` (D-IMPL-86"
                " correction, 2026-08-05); after the engine has run, a product"
                " has already been assembled from a set the deployment's own"
                " claim may contradict."
            )

    # (2) the plan bound is the plan run
    if demanded:
        for execution in executions:
            if execution.plan_node is not None and _is_plan_construction(
                execution.plan_node, plan_classes
            ):
                # The plan comes into being INSIDE the call expression that
                # consumes it, so it is not an object any binder could have been
                # handed — whatever the binder above was given, it was something
                # else. This is why 15.1-04 recorded the hoist as required rather
                # than cosmetic: until the plan is a named local there is no
                # statement the binder call can occupy.
                problems.append(
                    f"{where}:{execution.lineno}: `ProjectionEngine.execute` is"
                    " handed a plan constructed inline as its own `"
                    f"{ENGINE_PLAN_KEYWORD}=` argument, so no `{BINDER_CALL}`"
                    " call can have been handed that object. Hoist the plan into"
                    " a local and call the binder on the line between (D-IMPL-86"
                    " correction, 2026-08-05)."
                )
                continue
            if execution.plan is None:
                continue  # an unreadable plan expression — a stated limit, not a pass
            if any(
                call.handed == execution.plan and call.position < execution.position
                for call in calls
            ):
                continue
            problems.append(
                f"{where}:{execution.lineno}: `ProjectionEngine.execute` runs"
                f" `{_render(execution.plan)}`, which no `{BINDER_CALL}` call in"
                " this body was handed beforehand. Naming the binder over some"
                " OTHER plan leaves the plan that actually assembles the product"
                f" unbound. Hand `{BINDER_CALL}` the same object"
                " `ProjectionEngine.execute` will run (D-IMPL-86 correction,"
                " 2026-08-05)."
            )

    return problems


def _delegates_the_seam_to_the_resolver(
    path: pathlib.Path, scope: ast.AST
) -> bool:
    """Does this body hand the plan-construction -> execution seam to the SDK?

    `D-IMPL-300`. The binder must be called between plan construction and
    :meth:`~ccf.projection.engine.ProjectionEngine.execute`. A body that builds
    a plan and executes it OWNS that seam and must name the binder. A body that
    builds a plan and hands it to
    :func:`~ccf.products.resolver.build_governed_resolver` does **not** own it:
    ``plan_factory`` is invoked inside :class:`~ccf.products.resolver.
    GovernedResolver`, which calls the binder itself, and requiring the example
    to name it too would put the governance call back into adopter code — the
    plumbing cp-05's migration removed.

    **ARCHITECTURAL, NOT NOMINAL.** The question asked is *"who owns the
    seam?"*, answered from the tree: the module reaches the canonical resolver,
    and this body never executes a projection itself. No example name appears
    here, so cp-06 and everything after it are covered by the same rule without
    an edit.

    The two conditions are conjunctive on purpose. A module that both delegates
    *and* runs its own engine somewhere still owns a seam in the body that
    executes, and that body keeps the requirement.
    """
    module = _parse(path)
    if module is None:
        return False
    reaches_resolver = any(
        isinstance(node, ast.Name) and node.id in CANONICAL_RESOLVER_ENTRYPOINTS
        or isinstance(node, ast.Attribute)
        and node.attr in CANONICAL_RESOLVER_ENTRYPOINTS
        for node in ast.walk(module)
    )
    if not reaches_resolver:
        return False
    return not any(_is_plan_execution(node) for node in _scope_nodes(scope))


def _projecting_scopes() -> list[tuple[pathlib.Path, ast.AST]]:
    """Every lexical body under ``examples/`` that plans or runs a projection."""
    found: list[tuple[pathlib.Path, ast.AST]] = []
    for path in _python_sources(BINDER_SCANNED_TREES):
        tree = _parse(path)
        if tree is None:
            continue
        for scope in _scopes(tree):
            for node in _scope_nodes(scope):
                if _is_plan_construction(node) or _is_plan_execution(node):
                    found.append((path, scope))
                    break
    return found


def test_the_binder_scan_is_not_vacuous() -> None:
    """The floor is counted from the tree, and asserted rather than assumed.

    **Why the floor sits exactly at the observed count, with no headroom.**
    Headroom is not slack, it is a licence: a floor of 9 against 11 bodies lets
    two projecting bodies stop being scanned with nothing failing to say so,
    which is the same silent-loss failure the floor exists to prevent. The
    tight floor is the strong setting and the `>=` direction is the safe one.

    What the tightness costs is that a *legitimate* removal — retiring an
    example, merging two bodies — presents as red and is fixed by the identical
    edit an accidental removal needs, so nothing at the failure site tells the
    two apart. That is a real cost and it is paid deliberately, because the
    alternative pays it in the other direction, where the loss is silent. The
    failure message therefore carries the one thing that *does* distinguish
    them afterwards: the instruction to name the removed site in the commit
    message, so the git history separates what the constant cannot.
    """
    found = _projecting_scopes()
    assert len(found) >= MINIMUM_PROJECTING_BODIES, (
        f"{len(found)} projecting bodies found,"
        f" {MINIMUM_PROJECTING_BODIES} expected. {FLOOR_REMOVAL_INSTRUCTION}"
        " Found: "
        + str(
            [
                f"{path.relative_to(REPO_ROOT)}:{_scope_line(scope)}"
                f" {_scope_label(scope)}"
                for path, scope in found
            ]
        )
    )


def _one_document_deployments() -> list[str]:
    """Every deployment claiming the D-IMPL-137 exemption, by root."""
    claimed: set[str] = set()
    for path, scope in _projecting_scopes():
        if _one_document(scope, path, _bindings(scope)):
            root = _deployment_root(path)
            if root is not None:
                claimed.add(str(root.relative_to(REPO_ROOT)))
    return sorted(claimed)


def _sdk_supplied_deployments() -> list[str]:
    """Every deployment claiming the `D-IMPL-141` SDK-supplied exemption, by root."""
    claimed: set[str] = set()
    for path, scope in _projecting_scopes():
        if _sdk_supplied_operator_set(scope, path):
            root = _deployment_root(path)
            if root is not None:
                claimed.add(str(root.relative_to(REPO_ROOT)))
    return sorted(claimed)


def _roster_problems(
    claimed: list[str], *, ruled: frozenset[str], label: str
) -> list[str]:
    """Whether ``claimed`` is exactly the roster ``ruled``, named by ``label``.

    A predicate rather than an inline comparison, so each roster test and its
    control judge by the same code — the same reason :func:`_gate_collapses`
    and :func:`_binder_collapses` are predicates. Parameterised on the roster
    so the second exemption gets the identical instrument rather than a second
    copy of it that drifts.

    **Set equality rather than a ceiling** (Dave, 2026-08-27). A ceiling reads
    ``len(claimed) <= n`` and is therefore blind to a SWAP: a ruled deployment
    leaving while an unruled one arrives holds the number and moves the
    membership, which is the failure mode that audits clean forever. Arrivals
    and departures are reported as separate problems because they are different
    faults — an arrival is an unruled claim on the exemption, a departure is a
    ruled record that has stopped describing the tree — and a caller seeing
    both at once is looking at exactly the swap a count would have missed.

    **Empty is red, not clean.** ``claimed == []`` reports every ruled member as
    departed rather than returning ``[]``, so a detector that has stopped
    matching anything cannot read as compliance. That is the posture
    ``tools/publish_scan.py::require_populated`` states — *refusing to report
    clean over an empty tree* — and it is the half a ceiling could never have:
    ``len([]) <= n`` is true for every ``n``.
    """
    arrived = sorted(set(claimed) - ruled)
    departed = sorted(ruled - set(claimed))
    problems: list[str] = []
    if arrived:
        problems.append(
            f"{arrived} claim the {label} exemption and are NOT on its roster."
            f" A human rules on each addition."
            f" {FLOOR_REMOVAL_INSTRUCTION} Ruled: {sorted(ruled)}"
        )
    if departed:
        problems.append(
            f"{departed} are on the {label} roster and no longer claim the"
            f" exemption — the ruled record has stopped describing the tree."
            f" {FLOOR_REMOVAL_INSTRUCTION} Claimed: {sorted(claimed)}"
        )
    return problems


def _exemption_problems(claimed: list[str]) -> list[str]:
    """Whether the D-IMPL-137 claimants are exactly the ruled roster."""
    return _roster_problems(
        claimed,
        ruled=RULED_ONE_DOCUMENT_DEPLOYMENTS,
        label="D-IMPL-137 one-document",
    )


def _sdk_supplied_problems(claimed: list[str]) -> list[str]:
    """Whether the D-IMPL-141 claimants are exactly the ruled roster."""
    return _roster_problems(
        claimed,
        ruled=RULED_SDK_SUPPLIED_DEPLOYMENTS,
        label="D-IMPL-141 SDK-supplied",
    )


def test_the_one_document_exemption_has_not_spread() -> None:
    """The roster, which is the module's floor discipline inverted.

    A floor stops coverage shrinking silently. Nothing stopped the *exemption*
    spreading silently, and an exemption that spreads quietly is how a
    conditioned demand becomes no demand.
    :data:`RULED_ONE_DOCUMENT_DEPLOYMENTS` names its members for the same
    reason the floors carry no headroom — and names them rather than counting
    them so that a swap is red too, not only a growth.
    """
    problems = _exemption_problems(_one_document_deployments())
    assert not problems, "; ".join(problems)


def test_the_sdk_supplied_exemption_has_not_spread() -> None:
    """The second ceiling, held to the identical discipline as the first.

    ``D-IMPL-141``'s shape is the one that ships now, so this is the exemption
    the *next* example is most likely to want. Its ceiling has no headroom for
    the same reason the other has none: a deployment that authors no operator
    set is a deployment nothing in ``examples/`` holds to the binder demand, and
    a population of those that can grow quietly is a demand that quietly ends.
    """
    problems = _sdk_supplied_problems(_sdk_supplied_deployments())
    assert not problems, "; ".join(problems)


def test_the_two_exemptions_are_disjoint() -> None:
    """No deployment claims both, so neither ceiling is counting the other's.

    Two ceilings of one only bound two populations if the populations are two.
    A deployment satisfying both predicates would be counted once in each and
    the pair would silently permit two claimants where each constant says one.
    """
    overlap = set(_one_document_deployments()) & set(_sdk_supplied_deployments())
    assert not overlap, (
        "these deployments claim BOTH exemptions, so the two ceilings are not"
        f" bounding disjoint populations: {sorted(overlap)}"
    )


@pytest.mark.parametrize(
    ("path", "scope"),
    _projecting_scopes(),
    ids=lambda value: (
        str(value.relative_to(REPO_ROOT)) if isinstance(value, pathlib.Path) else ""
    ),
)
def test_every_projecting_example_body_names_the_binder(
    path: pathlib.Path, scope: ast.AST
) -> None:
    """D-IMPL-86 element (3), as corrected 2026-08-05 — the **coverage** half.

    The binder returns ``None``, so no runtime evidence of the call exists and
    an AST check is the only mechanism there is. This asserts the call is
    *named*. Whether it does anything is
    :func:`test_no_projecting_body_names_the_binder_without_binding_it`, and
    keeping the two apart is deliberate: CR-03 was the finding that this
    assertion had been *read* as the second one, which it never was.

    What is still not asserted, stated exactly: **reachability**, and **execution
    order inside a loop**. A binder call inside a never-taken ``if``, an
    ``except`` handler, or a ``# pragma: no cover`` branch is named, is ordered
    before the engine, and never runs; and a plan rebuilt at the bottom of a
    loop body is in force at the top of it from the second iteration on
    (R4-WR-03). Source ordering is checkable from positions and is now checked;
    neither of those two is readable from an AST walk over one body, and both
    are left named rather than implied away.

    And the one that is larger than either, because it is not a limit of what an
    AST can read but a deliberate carve-out: **the D-IMPL-137 exemption
    itself**. A body in a deployment registering no
    ``ccf.projection-requirements`` whose plan's ``required=`` reads the product
    class's own claim is not asserted against here **at all** — this assertion
    returns before it runs, and :func:`_binder_collapses`'s properties (2) and
    (3) are switched off for the same body, so nothing reports it. That is
    intended: there is no second document for the binder to compare, so there is
    no demand. What bounds which such bodies exist is a **roster** —
    :data:`RULED_ONE_DOCUMENT_DEPLOYMENTS`, asserted by
    :func:`test_the_one_document_exemption_has_not_spread` — and not anything
    this assertion reads.

    **The same carve-out now has a second route**, and it is bounded the same
    way rather than folded into the first:
    :func:`_sdk_supplied_operator_set`, the `D-IMPL-141` shape where the
    deployment authors no operator set at all because
    :func:`~ccf.products.resolver.build_governed_resolver` hands it one.
    Its roster is :data:`RULED_SDK_SUPPLIED_DEPLOYMENTS`, asserted by
    :func:`test_the_sdk_supplied_exemption_has_not_spread`.
    """
    if _delegates_the_seam_to_the_resolver(path, scope):
        # `D-IMPL-300`. This body builds a plan and hands it to the canonical
        # resolver; it never executes one. `GovernedResolver` calls the binder
        # between `plan_factory(...)` and `ProjectionEngine.execute`, which is
        # the ruled point and — since the factory is invoked inside the SDK —
        # the only point that still exists. Requiring the example to name the
        # binder as well would be requiring it to duplicate a check the SDK
        # performs, which is the adopter plumbing canonical adoption removes.
        #
        # The invariant is unchanged in force, only in scope: a body that owns
        # the seam still names the binder, and this predicate says who owns it.
        return
    if _premise_is_false(scope, path, _bindings(scope)):
        # Either route. Row B: the deployment registers no
        # `ccf.projection-requirements` AND its plan's `required=` reads the
        # product class's own claim, so the binder would compare a value
        # against itself — the shape `_binder_collapses` property (1) refuses.
        # `D-IMPL-141`: the deployment's `binding.yaml` names this function
        # through `plan:`, and every plan it builds is built from the operator
        # set the SDK handed it — so the binder would compare that same
        # SDK-derived set against itself, which property (1) refuses for
        # exactly the same reason.
        #
        # Each route is bounded by its own ceiling test, not by this early
        # return, and row C is refused by both predicates.
        return
    assert _names_the_binder(scope), (
        f"{path.relative_to(REPO_ROOT)}:{_scope_line(scope)}:"
        f" {_scope_label(scope)} constructs or runs a projection plan without"
        f" naming `{BINDER_CALL}`. The product class's"
        " `required_operator_keys` and the projection's own"
        " `required_operator_keys` are two separately authored documents"
        " (design E2, D-IMPL-86 element (2)); the binder is the only thing"
        " that holds them in agreement, and it must be called between plan"
        " construction and `ProjectionEngine.execute` (D-IMPL-86 correction,"
        " 2026-08-05). Import it from `ccf.deployment` and call it on the"
        " line after the plan becomes a named local."
    )


def test_the_binder_tripwire_detects_a_projection_that_skips_it() -> None:
    """Watched to fire, and watched to stay quiet.

    The third probe is the one that matters most for this phase: a body that
    constructs a plan and **returns** it without executing — the shape both
    replay environments' ``resolve_plan`` methods have — is a projecting body
    and is satisfied by the binder alone. A tripwire that demanded an
    ``execute`` call alongside the binder would be red on two correct sites.
    """
    plan = f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid, {PLAN_REQUIRED_KEYWORD}=keys)"
    execute = f"ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)"

    unbound = (
        # plans and executes, never binds
        "def serve(pid, keys, r, declared):\n"
        f"    plan = {plan}\n"
        f"    return {execute}\n",
        # constructs a plan and returns it, never binds — the replay shape,
        # done wrong
        "def resolve_plan(pid, keys, declared):\n"
        f"    return {plan}\n",
    )
    for source in unbound:
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _names_the_binder(function), source
        assert any(
            _is_plan_construction(node) or _is_plan_execution(node)
            for node in _scope_nodes(function)
        ), source

    bound = (
        # the compliant shape: hoisted plan, binder, then the engine
        "def serve(pid, keys, r, declared):\n"
        f"    plan = {plan}\n"
        f"    {BINDER_CALL}(declared=declared, plan=plan)\n"
        f"    return {execute}\n",
        # the replay shape, done right: plan, bind, return — no engine here
        "def resolve_plan(self, pid, keys):\n"
        f"    plan = {plan}\n"
        f"    {BINDER_CALL}(declared=self._declared, plan=plan)\n"
        "    return plan\n",
    )
    for source in bound:
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert _names_the_binder(function), source

    # …and a body that runs a workflow rather than a projection is not swept
    # in: `engine.execute(workflow, execution_id=...)` passes no `plan`.
    workflow = ast.parse(
        "def drive(engine, workflow, execution_id):\n"
        "    return engine.execute(workflow, execution_id=execution_id)\n"
    ).body[0]
    assert isinstance(workflow, ast.FunctionDef)
    assert not any(
        _is_plan_construction(node) or _is_plan_execution(node)
        for node in _scope_nodes(workflow)
    )


def test_the_premise_detector_reads_the_shipped_tree_correctly() -> None:
    """Every exemption is pinned to its cause, not to a deployment passing.

    **The substantive assertion is the first one, and it is stronger than the
    named list it used to be.** A projecting deployment that registers no
    ``ccf.projection-requirements`` has *some* explanation, and there are
    exactly two the module accepts: it authored one document where two were
    possible (row B), or it authored none because the SDK supplied the set
    (``D-IMPL-141``). A root in neither list is `D-IMPL-137` **row C** — a
    second operator set authored somewhere the Control Plane does not know
    about — and row C is precisely what must not appear quietly. Asserting
    set equality says *no root escapes registration unexplained*, which the
    previous single-name list could only say for as long as there was one.

    The two named assertions that follow keep each route pinned to the
    deployment that actually exercises it, so a route that silently stopped
    matching its own subject — and started matching something else — is red
    rather than merely differently-green.
    """
    roots = {
        _deployment_root(path)
        for path, _ in _projecting_scopes()
    }
    roots.discard(None)
    unregistered = sorted(
        str(root.relative_to(REPO_ROOT))
        for root in roots
        if not _registers_requirements(root)
    )
    row_b = _one_document_deployments()
    sdk_supplied = _sdk_supplied_deployments()

    assert unregistered == sorted({*row_b, *sdk_supplied}), (
        "a projecting deployment registers no `ccf.projection-requirements` and"
        " claims NEITHER exemption — that is D-IMPL-137 row C, a second"
        " operator set authored where the Control Plane cannot see it."
        f" unregistered={unregistered} row_b={row_b} sdk_supplied={sdk_supplied}"
    )
    # Both `D-IMPL-137` shapes are pinned by name, and `cp-04` is pinned
    # SEPARATELY from the two that precede it because it reaches row B by the
    # other route (`_supplied_by_the_product_class`, `D-IMPL-234`). A single
    # merged list would stay green if that route stopped matching and the older
    # reading started matching cp-04 for some unrelated reason — the
    # "differently-green" failure this test's own docstring names.
    #
    # cp-01/02/03 appear here and NOT on the roster: they claim the exemption
    # unruled, `D-IMPL-234` expressly declined to rule them in, and
    # `test_the_one_document_exemption_has_not_spread` is red on exactly those
    # three by that number. This assertion describes the tree; that one
    # describes what was ruled. They disagree on purpose.
    assert row_b == [
        "examples/cp-00-institutional-holders",
        "examples/cp-01-counterparty-reference-snapshot",
        "examples/cp-02-facility-terms-snapshot",
        "examples/cp-03-obligor-financial-spread",
        "examples/cp-04-corporate-family-tree",
        # `examples/cp-05-credit-exposure-rollup` JOINED row B on 2026-09-08
        # and LEFT it at its canonical adoption (`D-IMPL-298`, `D-IMPL-301`).
        # It is not a one-document deployment any more because it authors no
        # document at all: `GovernedResolver` supplies the operator set, so it
        # reads on the SDK-supplied list below instead. This list DESCRIBES THE
        # TREE, so it moves when the tree does — which is what just happened.
        #
        # And `examples/s1-00-companies-over-revenue` LEFT row B on 2026-09-09
        # by the same route (`D-IMPL-311`). Its hand-composed producer built its
        # plan from `scenario.product_class.required_operator_keys` — one
        # document where two were possible — and its named `plan_factory` now
        # authors nothing, taking the operator set from the `required` the SDK
        # hands it. Two examples have now crossed this boundary in the same
        # direction, which is what the modernization pass is for.
    ], row_b
    assert _supplied_by_the_product_class(
        *next(
            (scope, path, _deployment_root(path))
            for path, scope in _projecting_scopes()
            if str(path.relative_to(REPO_ROOT)).startswith(
                "examples/cp-04-corporate-family-tree/"
            )
        )
    ), "cp-04 must reach row B by the D-IMPL-234 route, not by the older reading"
    # cp-05 arrives here from row B above, by `D-IMPL-301`'s second shape: it
    # reaches `build_governed_resolver` directly rather than through a
    # `binding.yaml`, and the ownership condition is architectural rather than
    # tied to one wiring mechanism. The transition across these two lists is
    # the migration's own evidence — *one document where two were possible* ->
    # *no second document, because the SDK supplies the canonical set*.
    assert sdk_supplied == [
        # `D-IMPL-315`, 2026-09-10 — the canonical rung-4 successor, and the
        # first entry here that arrived from NEITHER list. cp-05 and s1-00
        # crossed the boundary by migration; this tree was AUTHORED on this
        # side of it, against the current surface rather than derived from the
        # frozen cp-04 specimen it succeeds. The detector reaches it from the
        # tree alone — this assertion and the roster both record that, and
        # neither causes it.
        "examples/cp-04-canonical-corporate-family-tree",
        "examples/cp-05-credit-exposure-rollup",
        # `D-IMPL-315`, 2026-09-10 — rung 6. The detector reaches it from the
        # tree alone; this assertion and the roster both record that answer and
        # neither causes it.
        "examples/cp-06-collateral-and-setoff-coverage",
        # `D-IMPL-315`, 2026-09-10 — rung 7, reached from the tree alone like
        # its rung-4 and rung-6 siblings.
        "examples/cp-07-client-360-coverage-graph",
        # `D-GATE-cp-08`, 2026-09-11 — rung 8. **This list DESCRIBES THE TREE**,
        # and it described it wrongly from the moment cp-08 shipped canonical:
        # the detector has reached this root since that commit and the literal
        # never said so. Stale independently of the roster, and completed here
        # in the same sitting as the roster admission (Dave, 2026-09-12) but as
        # its own assertion, because the two say different things — the roster
        # records what was RULED, this records what the detector ANSWERS.
        "examples/cp-08-covenant-in-force-as-of",
        # `D-IMPL-141`, 2026-09-12 — rung 9. Reached from the tree alone, like
        # its siblings above: this assertion and the roster both record that
        # answer and neither causes it.
        "examples/cp-09-treasury-liquidity-position",
        # `D-GATE-cp-10`, 2026-09-12 — rung 10, added in the same sitting as
        # the roster admission above but as its OWN assertion, because the two
        # say different things: the roster records what was RULED, this records
        # what the detector ANSWERS. cp-08 is the recorded case of those two
        # diverging — the detector had reached that root since the commit it
        # shipped canonical, and this literal did not say so for a day.
        "examples/cp-10-rating-and-spread-migration",
        # `D-GATE-cp-11`, 2026-09-12 — rung 11, added in the same sitting as
        # the roster admission above but as its OWN assertion, because the two
        # say different things: the roster records what was RULED, this records
        # what the detector ANSWERS. cp-08 is the recorded case of those
        # diverging — the detector had reached that root since the commit it
        # shipped canonical, and this literal did not say so for a day.
        "examples/cp-11-credit-surveillance-early-warning",
        "examples/hw1-companies-over-revenue/deployment",
        # `D-IMPL-311`, 2026-09-09 — s1-00 arrives from row B above, by the
        # same second shape cp-05 took: it reaches `build_governed_resolver`
        # directly rather than through a `binding.yaml`.
        "examples/s1-00-companies-over-revenue",
    ], (
        sdk_supplied
    )


# --------------------------------------------------------------------------
# Controls for the D-IMPL-141 route. A detector taught to recognise a shape can
# just as easily be taught to recognise nothing, so each condition it rests on
# is broken in turn against a `tmp_path` deployment and watched to refuse.
# --------------------------------------------------------------------------


#: The shipped shape, reduced to its skeleton: a projection class satisfying the
#: Protocol structurally, and a factory that returns one built from the operator
#: set it was handed. Built from the module's own constants so a rename of
#: either keyword reaches this fixture rather than leaving it stale.
_FACTORY_MODULE = (
    "class _Projection:\n"
    f"    def __init__(self, *, {PLAN_REQUIRED_KEYWORD}):\n"
    f"        self._required = {PLAN_REQUIRED_KEYWORD}\n"
    "    def required_operators(self):\n"
    "        return self._required\n"
    "    def invoke(self, **kwargs):\n"
    "        return None\n"
    "\n"
    f"def build_projection(*, {FACTORY_REQUIRED_PARAMETER}, request):\n"
    f"    return _Projection({PLAN_REQUIRED_KEYWORD}={FACTORY_REQUIRED_PARAMETER})\n"
)


def _factory_deployment(
    root: pathlib.Path,
    *,
    module: str = _FACTORY_MODULE,
    binding: str | None = f"{REFERENCE_KEYS[0]}: projection.py:build_projection\n",
    config: bool = True,
) -> tuple[pathlib.Path, ast.AST]:
    """Synthesize a `D-IMPL-141`-shaped deployment and return its factory scope.

    Returns ``(module path, the factory's scope)``. Every control below builds
    one of these and breaks exactly one condition, so a refusal names the
    condition that produced it rather than the composition.
    """
    root.mkdir(parents=True, exist_ok=True)
    if config:
        (root / SINGLE_FILE_CONFIG_NAME).write_text("semver: '1.0.0'\n", encoding="utf-8")
    if binding is not None:
        (root / BINDING_DOCUMENT_NAME).write_text(binding, encoding="utf-8")
    path = root / "projection.py"
    path.write_text(module, encoding="utf-8")
    tree = ast.parse(module)
    scope = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build_projection"
    )
    return path, scope


def test_the_binding_documents_reference_surface_is_still_one_key() -> None:
    """The import above must keep naming the key the SDK actually reads.

    :data:`REFERENCE_KEYS` is a **one-element** tuple by ruling (Amendment A.3),
    and this module indexes ``[0]`` to get the plan key. If the SDK ever widens
    it, indexing zero silently reads whichever key happens to sort first — so
    the widening turns this red instead.
    """
    assert REFERENCE_KEYS == ("plan",), REFERENCE_KEYS
    assert BINDING_DOCUMENT_NAME == "binding.yaml", BINDING_DOCUMENT_NAME


def test_the_factory_seam_still_names_its_operator_set_parameter() -> None:
    """The parameter this route keys on is the one the Protocol declares.

    :data:`FACTORY_REQUIRED_PARAMETER` is an assumption about someone else's
    signature. Asserted against the shipped Protocol rather than believed, so a
    rename there turns this red rather than making the detector match nothing
    and hand out no exemptions — which would look like the gate tightening.
    """
    import inspect

    from ccf.products.resolver import ProjectionPlanFactoryProtocol

    parameters = inspect.signature(ProjectionPlanFactoryProtocol.__call__).parameters
    assert FACTORY_REQUIRED_PARAMETER in parameters, sorted(parameters)


def test_the_product_class_surface_still_names_its_operator_set() -> None:
    """The two names the `D-IMPL-234` route keys on are the SDK's, not ours.

    Both are assumptions about someone else's vocabulary, and a rename in either
    place must turn THIS red. The failure mode being bought off is specific and
    quiet: an unasserted rename would make
    :func:`_config_declares_operator_set` read ``None`` and
    :func:`_supplied_by_the_product_class` return ``False`` for every body, so
    the route would hand out no exemptions at all — which reads as the gate
    getting *stricter* and would sail past any check watching only for
    over-permission. The same reasoning
    :func:`test_the_factory_seam_still_names_its_operator_set_parameter` gives
    for the `D-IMPL-141` route's parameter.
    """
    from ccf.controlplane.artifacts import ProductClassDeclaration
    from ccf.deployment.config import _RESERVED_SECTIONS

    assert PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE in ProductClassDeclaration.model_fields, (
        sorted(ProductClassDeclaration.model_fields)
    )
    assert PRODUCT_CLASS_SECTION in _RESERVED_SECTIONS, sorted(_RESERVED_SECTIONS)


def test_the_sdk_supplied_route_recognises_the_shipped_shape(
    tmp_path: pathlib.Path,
) -> None:
    """The controls' baseline: refusals below must come from the breakage."""
    path, scope = _factory_deployment(tmp_path / "examples" / "zz-demo")
    # The synthesized tree is not under the real `examples/`, so the artifact
    # root check would refuse it for the right reason at the wrong moment.
    # Exercised against the SHIPPED example instead, which is the subject.
    shipped = (
        REPO_ROOT / "examples" / "hw1-companies-over-revenue" / "deployment"
        / "projection.py"
    )
    tree = _parse(shipped)
    assert tree is not None
    factory = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build_projection"
    )
    assert _sdk_supplied_operator_set(factory, shipped), (
        "the D-IMPL-141 route no longer recognises the shipped example, so the"
        " exemption it grants is granted to nothing and the controls below"
        " would all pass over a detector that matches zero bodies"
    )
    assert path.is_file()  # the synthesized fixture is used by the controls


@pytest.mark.parametrize(
    ("label", "kwargs"),
    [
        (
            "no binding document at all",
            {"binding": None},
        ),
        (
            "a binding document naming a different module",
            {"binding": f"{REFERENCE_KEYS[0]}: elsewhere.py:build_projection\n"},
        ),
        (
            "a binding document naming a different attribute",
            {"binding": f"{REFERENCE_KEYS[0]}: projection.py:build_something_else\n"},
        ),
        (
            "a binding document with no plan reference",
            {"binding": "config: ccf_config.yaml\n"},
        ),
        (
            "no Control Plane authoring surface at all",
            {"config": False, "binding": None},
        ),
    ],
)
def test_the_sdk_supplied_route_refuses_a_broken_condition(
    tmp_path: pathlib.Path, label: str, kwargs: dict[str, object]
) -> None:
    """Each condition broken in turn, against a real `examples/` subtree.

    Written under ``REPO_ROOT / "examples"`` is impossible for a fixture, so the
    detector is exercised on a synthesized root and the artifact-root condition
    is asserted separately below. What these prove is that the *binding-document*
    conditions each refuse on their own — the load-bearing one, because it is
    the Control Plane's own statement that the SDK reaches this function.
    """
    root = tmp_path / "deployment"
    path, scope = _factory_deployment(root, **kwargs)  # type: ignore[arg-type]
    assert not _sdk_supplied_operator_set(scope, path), label


def test_the_sdk_supplied_route_refuses_a_plan_built_from_another_source(
    tmp_path: pathlib.Path,
) -> None:
    """Row C, in the new shape: an operator set authored somewhere else.

    The factory takes the SDK's set and then builds its plan from a different
    value. That is a second authored operator set the Control Plane cannot see,
    and it must stay subject to the demand — otherwise this route would launder
    exactly what `D-IMPL-137` row C exists to keep red.
    """
    module = _FACTORY_MODULE.replace(
        f"    return _Projection({PLAN_REQUIRED_KEYWORD}={FACTORY_REQUIRED_PARAMETER})",
        f"    return _Projection({PLAN_REQUIRED_KEYWORD}=request.my_own_keys)",
    )
    root = tmp_path / "deployment"
    path, scope = _factory_deployment(root, module=module)
    assert f"{PLAN_REQUIRED_KEYWORD}=request.my_own_keys" in module
    assert not _sdk_supplied_operator_set(scope, path)


def test_the_sdk_supplied_route_refuses_a_factory_that_builds_no_plan(
    tmp_path: pathlib.Path,
) -> None:
    """**The zero-match control.** Matching nothing is not satisfying anything.

    A body constructing no plan at all yields an empty source tuple, and
    ``all(...)`` over an empty tuple is ``True`` — so without the explicit
    emptiness guard this route would hand the exemption to every function the
    binding document happens to name, including one that does nothing. That is
    the vacuous-pass shape this whole phase has been finding.
    """
    module = (
        f"def build_projection(*, {FACTORY_REQUIRED_PARAMETER}, request):\n"
        "    return None\n"
    )
    root = tmp_path / "deployment"
    path, scope = _factory_deployment(root, module=module)
    assert _constructed_plan_sources(scope) == ()
    assert not _sdk_supplied_operator_set(scope, path)


def test_the_sdk_supplied_route_refuses_a_body_with_no_artifact_tree() -> None:
    """Fail-closed, the same way :func:`_one_document` is.

    A tree outside ``examples/`` has made no claim to have a Control Plane at
    all, so it cannot buy an exemption by having nothing to check against.
    """
    nowhere = REPO_ROOT / "nowhere" / "projection.py"
    scope = next(
        node
        for node in ast.walk(ast.parse(_FACTORY_MODULE))
        if isinstance(node, ast.FunctionDef) and node.name == "build_projection"
    )
    assert _deployment_root(nowhere) is None
    assert not _sdk_supplied_operator_set(scope, nowhere)


def test_the_sdk_supplied_route_refuses_a_deployment_that_registers_requirements(
    tmp_path: pathlib.Path,
) -> None:
    """Two documents means two documents, whatever shape the code is in.

    A deployment that registers a ``ccf.projection-requirements`` HAS authored a
    second operator set. The demand stands even if its factory looks exactly
    like the exempt one — which is the condition that stops this route becoming
    a way to opt out of the binder by adopting a file layout.
    """
    root = tmp_path / "deployment"
    path, scope = _factory_deployment(root)
    (root / SINGLE_FILE_CONFIG_NAME).write_text(
        f"class_id: {REQUIREMENTS_CLASS_ID}\n", encoding="utf-8"
    )
    assert _registers_requirements(root)
    assert not _sdk_supplied_operator_set(scope, path)


def test_each_roster_refuses_an_unruled_claimant() -> None:
    """Both rosters, watched failing on all three faults they can report.

    An **arrival** (a name nobody ruled on), a **departure** (a ruled name that
    has stopped claiming), and the **swap** that a ceiling could not see — one
    of each leaves the count unchanged and must still be red. The empty case is
    asserted last and is the vacuity control: a detector matching nothing must
    not read as compliance.
    """
    intruder = "examples/unruled-deployment"

    for problems_of, ruled, label in (
        (_exemption_problems, RULED_ONE_DOCUMENT_DEPLOYMENTS, "D-IMPL-137 one-document"),
        (_sdk_supplied_problems, RULED_SDK_SUPPLIED_DEPLOYMENTS, "D-IMPL-141 SDK-supplied"),
    ):
        ruled_list = sorted(ruled)

        arrived = problems_of([*ruled_list, intruder])
        assert arrived and label in arrived[0], (label, arrived)
        assert intruder in arrived[0], (label, arrived)

        departed = problems_of(ruled_list[1:])
        assert departed and ruled_list[0] in departed[0], (label, departed)

        swapped = problems_of([*ruled_list[1:], intruder])
        assert len(swapped) == 2, (label, swapped)
        assert len([*ruled_list[1:], intruder]) == len(ruled_list), (
            "the swap must hold the cardinality, or it is not testing what a"
            " ceiling would have missed"
        )

        assert problems_of([]), (
            f"{label}: an empty claim set must be RED. A roster that tolerates"
            " absence is a detector that has stopped matching and reads clean."
        )


def test_a_body_with_no_artifact_tree_is_subject_to_the_demand() -> None:
    """Fail-closed, and **this test is that guard's own control**.

    It stands in for no other test, and an earlier revision of this docstring
    said it did: the body synthesized below *does* assemble a `ProductLineage`,
    so `_class_claim` reads it and the second fail-closed guard does not answer
    first — the artifact-tree guard is what refuses it, and a regression in
    that guard is what this catches. The hazard it closes is an adopter tree
    outside `examples/` that assembles a lineage and reads one source, and
    would otherwise buy an exemption by having no Control Plane at all.

    The two helper assertions below are still worth pinning on their own, but
    they are not the whole test: the composition matters, and this synthesizes
    a body whose class claim and plan `required=` read the identical path —
    the AST agreement that WOULD grant the exemption once the artifact-tree
    check is out of the way. Asserting `_one_document` directly on that body
    is what proves the artifact-tree check overrides the agreement rather
    than the two happening not to interact.
    """
    no_tree = REPO_ROOT / "nowhere" / "run.py"
    assert _deployment_root(no_tree) is None
    assert not _registers_requirements(None)

    lineage = f"{LINEAGE_CONSTRUCTOR}({LINEAGE_DECLARED_KEYWORD}="
    plan = f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid, {PLAN_REQUIRED_KEYWORD}="
    source = (
        "def resolve_plan(pid, declared):\n"
        f"    {lineage}declared.required_operator_keys)\n"
        f"    plan = {plan}declared.required_operator_keys)\n"
        "    return plan\n"
    )
    tree = ast.parse(source)
    scope = next(s for s in _scopes(tree) if isinstance(s, ast.FunctionDef))
    bindings = _bindings(scope)

    # The agreement itself, pinned: the class claim and the plan's lone
    # `required=` resolve to the exact same path, not merely a shared prefix.
    # Under the pre-fix code this is what made `_one_document` return `True`
    # for a body with no artifact tree at all.
    claim = _class_claim(scope, bindings)
    sources = list(_plan_sources(scope, bindings).values())
    assert claim is not None
    assert sources == [claim], (claim, sources)

    assert not _one_document(scope, no_tree, bindings)


def test_a_row_b_deployment_claims_the_exemption_for_the_stated_reason() -> None:
    """Row B, pinned to its cause rather than to the specimen happening to pass.

    Both halves asserted separately, because either alone would keep passing if
    the other silently changed: the deployment registers no requirements
    artifact, and the body's plan reads the product class's own claim.

    **The specimen is `cp-00`, and it moved here on 2026-09-09** (`D-IMPL-311`).
    It was `examples/s1-00-companies-over-revenue`, which left row B at its
    canonical adoption — its `plan_factory` authors no operator set now, so a
    control asserting it *does* read one document was asserting something the
    ruling had just made false. `cp-00` is a row-B deployment on the same
    reading and constructs its plan from the identical expression, so this
    control keeps exactly the property it had. The name no longer says `hw1`,
    which it had not been pointed at for some time.
    """
    produce = REPO_ROOT / "examples" / "cp-00-institutional-holders" / "produce.py"
    root = _deployment_root(produce)
    assert root is not None and not _registers_requirements(root)

    tree = _parse(produce)
    assert tree is not None
    exempt = [
        scope
        for scope in _scopes(tree)
        if _one_document(scope, produce, _bindings(scope))
    ]
    assert exempt, "the row-B specimen's projecting body no longer reads one document"


def test_an_exempt_body_that_calls_the_binder_is_still_refused() -> None:
    """Property (1)'s unconditionality, watched rather than asserted (D-IMPL-137).

    This is the sentence that makes the ruling defensible: the exemption is an
    **absence of demand**, not a **licence**. A one-document deployment is not
    asked to call the binder — but if it calls it anyway over a plan built from
    the very claim it is about to be compared against, property (1) still
    refuses it for the tautology. Nothing is bought by claiming the exemption
    that could not be had without it.

    Until this control landed, that sentence appeared in the module docstring,
    in a comment inside :func:`_binder_collapses`, in
    :func:`test_every_projecting_example_body_names_the_binder`'s docstring and
    in `D-IMPL-137` itself — and **nothing tested it**. Folding property (1)
    under the ``if demanded:`` guard changes no verdict anywhere on the shipped
    tree and leaves every probe in this module passing, because every
    ``_binder_collapses`` probe here is *demanded* and the one exempt body
    makes no binder call. A future tidy-up doing exactly that would have been
    invisible to the whole suite.

    Run against HW-1's **real** ``produce.py`` path, the same way
    :func:`test_a_second_operator_set_outside_the_control_plane_is_refused`
    runs row C: a synthesized path resolves :func:`_deployment_root` to ``None``
    and the fail-closed default would refuse the body whatever its AST said, so
    the control would pass without ever reaching the exempt branch it exists to
    exercise. Both halves are asserted, because either alone would keep passing
    if the other silently changed — that the body IS exempt, and that it is
    refused regardless.
    """
    produce = REPO_ROOT / "examples" / "s1-00-companies-over-revenue" / "produce.py"
    assert _deployment_root(produce) is not None, (
        "this control needs HW-1's REAL artifact tree; a synthesized path is"
        " refused by the fail-closed default before the exempt branch is reached"
    )

    source = (
        "def serve(pid, r, declared):\n"
        f"    {LINEAGE_CONSTRUCTOR}({LINEAGE_DECLARED_KEYWORD}="
        f"{BINDER_DECLARED_KEYWORD}.required_operator_keys)\n"
        f"    plan = Fixture{PLAN_CLASS_SUFFIX}({PLAN_ID_KEYWORD}=pid,"
        f" {PLAN_REQUIRED_KEYWORD}={BINDER_DECLARED_KEYWORD}"
        ".required_operator_keys)\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=plan)\n"
        f"    return ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)\n"
    )
    function = ast.parse(source).body[0]
    assert isinstance(function, ast.FunctionDef)

    # exempt: HW-1 registers no requirements artifact, and this body's class
    # claim and plan `required=` read one source — row B, exactly
    assert _one_document(function, produce, _bindings(function)), source

    # …and refused anyway, by property (1), which the `if demanded:` guards do
    # not cover. This is the assertion the whole ruling rests on.
    problems = _binder_collapses(function, produce)
    assert problems, source
    assert all(
        "compares a value against itself" in problem for problem in problems
    ), problems


def test_a_second_operator_set_outside_the_control_plane_is_refused() -> None:
    """Row C — the shape the exemption must never admit (D-IMPL-137).

    The exemption is not "no artifact, no demand". It is earned by a positive
    reading: the deployment registers no `ccf.projection-requirements` AND its
    code demonstrably reads one source. A deployment that registers nothing
    while its plan's `required=` reads somewhere unrelated has authored a
    second operator set the Control Plane does not know about — the two
    readings disagree, and that disagreement is the finding.

    **Mutated in memory against the REAL deployment path, and that is
    load-bearing rather than tidy.** Copying the example under `tmp_path` and
    reading the copy resolves :func:`_deployment_root` to ``None``, so the
    fail-closed default refuses the body whatever its AST says — the control
    would pass without ever exercising row C, and would go on passing if row C
    broke. Parsing mutated source while passing the specimen's real path is what
    puts a real artifact tree, one that registers nothing, behind an AST that
    reads two sources.

    **The specimen is `cp-00`, and it moved here on 2026-09-09** (`D-IMPL-311`),
    for the reason the row-B control above records: s1-00's plan construction
    left with its migration, and the mutation had nothing left to rewrite.
    `cp-00` constructs its plan from the identical expression, so the mutation
    string below is unchanged.
    """
    produce = REPO_ROOT / "examples" / "cp-00-institutional-holders" / "produce.py"
    root = _deployment_root(produce)
    assert root is not None, "row C needs a REAL artifact tree, not a copy"
    assert not _registers_requirements(root), "the specimen registers no requirements"

    text = produce.read_text(encoding="utf-8")
    baseline = ast.parse(text)
    assert not [
        problem
        for scope in _scopes(baseline)
        for problem in _binder_collapses(scope, produce)
    ], "the unmutated specimen must be exempt, or this control proves nothing"

    mutated = text.replace(
        "required=tuple(scenario.product_class.required_operator_keys),",
        "required=tuple(scenario.operator_parameters),",
        1,
    )
    assert mutated != text, "the plan construction moved; update this control"

    problems = [
        problem
        for scope in _scopes(ast.parse(mutated))
        for problem in _binder_collapses(scope, produce)
    ]
    assert any(
        "with no `refuse_operator_set_divergence`" in problem for problem in problems
    ), problems


#: A ``cp-04``-shaped deployment reduced to its skeleton: a config authoring the
#: ONE operator set in the reserved section, and a projecting body whose plan
#: reads ``required=`` off that declaration. Built from the module's own
#: constants so a rename reaches this fixture rather than leaving it stale.
_PRODUCT_CLASS_CONFIG = (
    "semver: '1.0.0'\n"
    f"{PRODUCT_CLASS_SECTION}:\n"
    f"  {PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE}:\n"
    "    - policy.principal-subgraph\n"
    "    - traversal.typed-neighborhood\n"
)

_PRODUCT_CLASS_BODY = (
    "def project(scenario, reader):\n"
    f"    plan = Fixture{PLAN_CLASS_SUFFIX}({PLAN_ID_KEYWORD}=scenario.plan_id,"
    f" {PLAN_REQUIRED_KEYWORD}=tuple(scenario.{PRODUCT_CLASS_SECTION}"
    f".{PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE}))\n"
    f"    return ProjectionEngine(reader=reader).execute({ENGINE_PLAN_KEYWORD}=plan)\n"
)


def _product_class_deployment(
    root: pathlib.Path,
    *,
    config: str | None = _PRODUCT_CLASS_CONFIG,
    body: str = _PRODUCT_CLASS_BODY,
    requirements: str | None = None,
) -> tuple[pathlib.Path, ast.AST]:
    """Synthesize a `D-IMPL-234`-shaped deployment and return its projecting scope.

    ``requirements`` writes a SECOND operator-set document into the artifact
    tree — the sabotage (a) shape from `D-IMPL-234`'s contract, and the one fact
    that must withdraw the exemption however the AST reads.
    """
    root.mkdir(parents=True, exist_ok=True)
    if config is not None:
        (root / SINGLE_FILE_CONFIG_NAME).write_text(config, encoding="utf-8")
    if requirements is not None:
        (root / "artifacts").mkdir(exist_ok=True)
        (root / "artifacts" / "requirements.yaml").write_text(
            requirements, encoding="utf-8"
        )
    path = root / "produce.py"
    path.write_text(body, encoding="utf-8")
    scope = next(
        node
        for node in ast.walk(ast.parse(body))
        if isinstance(node, ast.FunctionDef) and node.name == "project"
    )
    return path, scope


def test_the_product_class_route_recognises_the_shipped_cp_04_shape() -> None:
    """The `D-IMPL-234` route's baseline: it matches the body it was ruled for.

    A detector taught to recognise a shape can just as easily be taught to
    recognise nothing, and a route matching zero bodies grants zero exemptions —
    which reads as the gate tightening and would leave every refusal control
    below passing over a dead function. Asserted against the SHIPPED example,
    which is the subject the ruling names.
    """
    shipped = [
        (path, scope)
        for path, scope in _projecting_scopes()
        if str(path.relative_to(REPO_ROOT)).startswith(
            "examples/cp-04-corporate-family-tree/"
        )
    ]
    assert shipped, "cp-04 has no projecting body; the ruling's subject moved"
    for path, scope in shipped:
        root = _deployment_root(path)
        assert not _registers_requirements(root), (
            "cp-04 registers a `ccf.projection-requirements` — it now has the"
            " TWO documents the binder's premise wants, and D-IMPL-234's"
            " exemption no longer describes it"
        )
        assert _supplied_by_the_product_class(scope, path, root), (
            f"{path.relative_to(REPO_ROOT)}:{_scope_line(scope)}"
        )
        assert _one_document(scope, path, _bindings(scope))


@pytest.mark.parametrize(
    ("label", "kwargs"),
    [
        ("no Control Plane authoring surface at all", {"config": None}),
        (
            "a config with no product_class section",
            {"config": "semver: '1.0.0'\n"},
        ),
        (
            "a product class declaring no operator set",
            {"config": f"semver: '1.0.0'\n{PRODUCT_CLASS_SECTION}:\n  ttl_anchor: x\n"},
        ),
        (
            "a product class whose operator set is empty",
            {
                "config": f"semver: '1.0.0'\n{PRODUCT_CLASS_SECTION}:\n"
                f"  {PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE}: []\n"
            },
        ),
        (
            "a plan built from a second set the Control Plane cannot see",
            {
                "body": _PRODUCT_CLASS_BODY.replace(
                    f"scenario.{PRODUCT_CLASS_SECTION}"
                    f".{PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE}",
                    "scenario.operator_parameters",
                )
            },
        ),
        (
            "a body that constructs no plan at all",
            {"body": "def project(scenario, reader):\n    return None\n"},
        ),
    ],
)
def test_the_product_class_route_refuses_a_broken_condition(
    tmp_path: pathlib.Path, label: str, kwargs: dict[str, object]
) -> None:
    """Each `D-IMPL-234` condition broken in turn, and watched to refuse.

    The fifth case is `D-IMPL-137` **row C** at this route — a second operator
    set authored where the Control Plane cannot see it — and it is the case that
    separates a positive reading from *"registers nothing, therefore exempt."*
    """
    path, scope = _product_class_deployment(tmp_path / "zz-demo", **kwargs)  # type: ignore[arg-type]
    assert not _supplied_by_the_product_class(scope, path, tmp_path / "zz-demo"), label


def test_a_second_registered_document_withdraws_the_product_class_exemption(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage (a) from `D-IMPL-234`'s contract, as a standing control.

    Dave's contract: *"a SECOND operator-set document in cp-04 that disagrees
    must go RED under the binder or a named refusal."* The exemption is a claim
    about the deployment's SHAPE, never about its name being on a roster, so the
    same body under a tree that registers a second — **disagreeing** — operator
    set must lose it. Registration is read by :func:`_registers_requirements`,
    which :func:`_one_document` consults before either route, so the withdrawal
    happens whatever the AST says.

    Both halves asserted: that the unsabotaged fixture IS recognised, and that
    the sabotaged one is refused. Either alone would keep passing if the other
    silently changed.
    """
    root = tmp_path / "zz-demo"
    path, scope = _product_class_deployment(root)
    assert _supplied_by_the_product_class(scope, path, root), (
        "the baseline fixture is not recognised, so the refusal below would"
        " prove nothing"
    )
    assert not _registers_requirements(root)

    # The second document, disagreeing with the config's two keys.
    sabotaged_path, sabotaged_scope = _product_class_deployment(
        root,
        requirements=(
            "semver: '1.0.0'\n"
            f"class_id: {REQUIREMENTS_CLASS_ID}\n"
            "declaration:\n"
            f"  {PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE}:\n"
            "    - similarity.nearest-neighbors\n"
        ),
    )
    assert _registers_requirements(root), (
        "a registered `ccf.projection-requirements` was not read, so the"
        " exemption would survive the very shape it must not survive"
    )
    # The AST is unchanged; the DOCUMENT is what withdrew the exemption.
    assert _supplied_by_the_product_class(sabotaged_scope, sabotaged_path, root), (
        "the route itself reads only the code and the one config, by design —"
        " the registration reading that refuses this body lives in"
        " `_one_document`, and the assertion above is what proves it fires"
    )


def test_a_cp_04_shaped_exempt_body_that_calls_the_binder_is_refused() -> None:
    """Sabotage (b) from `D-IMPL-234`'s contract, as a standing control.

    Dave's contract: *"a copy of ``produce.py`` carrying a DECORATIVE
    ``refuse_operator_set_divergence()`` must turn the tautology control RED."*
    This is the sentence that makes the new route defensible on the same terms
    `D-IMPL-137`'s routes are: the exemption is an **absence of demand**, not a
    **licence**. A body reaching row B by :func:`_supplied_by_the_product_class`
    is not asked to call the binder — but if it calls it anyway over the plan it
    built from the very declaration it is about to be compared against, the
    binder compares a value against itself, and :func:`_binder_collapses`
    property (1), which the ``if demanded:`` guards do not cover, still refuses
    it. Nothing is bought by claiming this exemption that could not be had
    without it.

    Run against cp-04's **real** ``produce.py`` path, the same way
    :func:`test_an_exempt_body_that_calls_the_binder_is_still_refused` runs
    HW-1's: a synthesized path resolves :func:`_deployment_root` to ``None`` and
    the fail-closed default would refuse the body whatever its AST said, so the
    control would pass without ever reaching the exempt branch it exists to
    exercise. Both halves are asserted — that the body IS exempt by this route,
    and that it is refused regardless.
    """
    produce = (
        REPO_ROOT / "examples" / "cp-04-corporate-family-tree" / "produce.py"
    )
    root = _deployment_root(produce)
    assert root is not None, (
        "this control needs cp-04's REAL artifact tree; a synthesized path is"
        " refused by the fail-closed default before the exempt branch is reached"
    )

    source = (
        "def serve(scenario, reader, declared):\n"
        f"    plan = Fixture{PLAN_CLASS_SUFFIX}({PLAN_ID_KEYWORD}=scenario.plan_id,"
        f" {PLAN_REQUIRED_KEYWORD}=tuple(scenario.{PRODUCT_CLASS_SECTION}"
        f".{PRODUCT_CLASS_OPERATOR_SET_ATTRIBUTE}))\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=scenario"
        f".{PRODUCT_CLASS_SECTION}, {ENGINE_PLAN_KEYWORD}=plan)\n"
        f"    return ProjectionEngine(reader=reader).execute("
        f"{ENGINE_PLAN_KEYWORD}=plan)\n"
    )
    function = ast.parse(source).body[0]
    assert isinstance(function, ast.FunctionDef)

    # exempt, and by the D-IMPL-234 route specifically
    assert _supplied_by_the_product_class(function, produce, root), source
    assert _one_document(function, produce, _bindings(function)), source

    # …and refused anyway, by property (1). This is what makes the exemption an
    # absence of demand rather than a licence.
    problems = _binder_collapses(function, produce)
    assert problems, source
    assert all(
        "compares a value against itself" in problem for problem in problems
    ), problems


def test_the_exemption_roster_refuses_a_third_claimant() -> None:
    """The roster fires on a THIRD claimant, watched rather than assumed.

    A constant nothing has been seen to trip is a constant nobody has tested.
    Exercised through `_exemption_problems`, the same predicate
    `test_the_one_document_exemption_has_not_spread` judges the tree by, against
    a synthesized third claimant — standing a real one up on disk would mean
    shipping it.

    Two was what Dave ruled on 2026-08-27, naming ``s1-00`` and ``cp-00``;
    `D-IMPL-234` made it three on 2026-09-01, naming ``cp-04``. **A FOURTH is
    what nobody has ruled on, and it is red here until somebody does** — which
    is not hypothetical: ``cp-01``, ``cp-02`` and ``cp-03`` are claiming it
    unruled on the shipped tree right now, and
    :func:`test_the_one_document_exemption_has_not_spread` is red on exactly
    those three by `D-IMPL-234`. The synthesized name below keeps this control
    independent of that standing red, so it still fires the day those three are
    ruled on.
    """
    assert not _exemption_problems(sorted(RULED_ONE_DOCUMENT_DEPLOYMENTS))
    problems = _exemption_problems(
        [*sorted(RULED_ONE_DOCUMENT_DEPLOYMENTS), "examples/cp-01-invented"]
    )
    assert problems and "cp-01-invented" in problems[0], problems


# --- tripwire (2), the argument half: the binder is doing something -----------


def _delegates_to_resolver(path: pathlib.Path) -> bool:
    """Does this module hand plan construction to the SDK's governed resolver?

    Resolved through the module's own ``from ccf... import``, never by bare
    name — the same discipline
    ``tests/examples/test_spine_separation.py::GOVERNED_SEAM_CALLS`` records,
    and for the same reason: a locally defined helper sharing a name is not an
    adoption.
    """
    tree = _parse(path)
    if tree is None:
        return False
    imported: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("ccf"):
            for alias in node.names:
                imported[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    owning = {
        "ccf.products.resolver.build_governed_resolver",
        "ccf.products.resolver.GovernedResolver",
    }
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and imported.get(node.func.id) in owning
        for node in ast.walk(tree)
    )


def _readable_binder_sites_in(
    path: pathlib.Path, scope: ast.AST
) -> list[str]:
    """Binder calls in one scope whose handed plan's ``required=`` is readable."""
    bindings = _bindings(scope)
    sources = _plan_sources(scope, bindings)
    return [
        f"{path.relative_to(REPO_ROOT)}:{call.lineno}"
        for call in _binder_calls(scope, bindings)
        if _handed_plan_source(call, sources, bindings) is not None
    ]


def _canonical_binder_ownership() -> list[str]:
    """The SDK's own binder calls, asserted AT the pre-execution point.

    `D-IMPL-300` ruled that `GovernedResolver` enforces operator-set divergence
    *before* the projection runs, so this reads the ordering out of the shipped
    module rather than accepting that a call is present somewhere in the file:
    a scope qualifies when it binds the very plan object it then hands to
    ``execute(plan=...)``, and binds it FIRST.

    **Why this and not the adopter scan's readability predicate.** The adopter
    scan calls a site readable when it can statically resolve the handed plan's
    ``required=``, which is what :func:`_binder_collapses` needs to compare. The
    resolver's plan comes from a caller-supplied ``plan_factory``, so its
    ``required=`` is genuinely unreadable here — correctly, and not as a defect.
    The property that matters for the canonical path is *order against
    execution*, and that is what is measured.

    It is deliberately NOT added to :data:`BINDER_SCANNED_TREES`. That tuple's
    membership is asserted by
    :func:`test_the_scan_root_membership_is_exactly_the_expected_sets` against
    the S-16 root-swap defect, and adding ``src`` there would move all three
    floors' universes at once.
    """
    path = REPO_ROOT / CANONICAL_BINDER_MODULE
    tree = _parse(path)
    if tree is None:  # pragma: no cover - a broken SDK module fails elsewhere
        return []
    found: list[str] = []
    for scope in _scopes(tree):
        calls = [node for node in _scope_nodes(scope) if isinstance(node, ast.Call)]
        # TWO PASSES, because `_scope_nodes` walks the tree rather than the
        # file: the execution can be reached before the bind that precedes it
        # on the page, and a single pass would then read a correct ordering as
        # a missing one.
        bound: dict[str, int] = {}
        for node in calls:
            if _callee(node) != BINDER_CALL:
                continue
            handed = _keyword(node, BINDER_PLAN_KEYWORD)
            if isinstance(handed, ast.Name):
                bound[handed.id] = node.lineno
        for node in calls:
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "execute"):
                continue
            executed = _keyword(node, BINDER_PLAN_KEYWORD)
            if not isinstance(executed, ast.Name):
                continue
            at = bound.get(executed.id)
            if at is not None and at < node.lineno:
                found.append(f"{path.relative_to(REPO_ROOT)}:{at}")
    return sorted(set(found))


def _resolved_binder_sites() -> list[str]:
    """ADOPTER-owned binder calls whose handed plan's ``required=`` is readable.

    The input :func:`_binder_collapses`'s first check consumes. A binder call
    whose plan is out of reach is scanned and says nothing, so counting the
    *readable* ones is what distinguishes a live check from a quiet one.

    **Scoped to deployments that have NOT adopted the resolver** (`D-IMPL-307`).
    A module that calls
    :func:`~ccf.products.resolver.build_governed_resolver` is not failing to
    bind — the SDK binds for it — and counting it here would put two
    architectures in one total where a decrement cannot be read. Its evidence
    is :func:`_delegated_binder_sites` instead. **Today the exclusion removes
    nothing:** no delegating module holds a direct binder call, so this count
    is the twelve it was before the split, and the separation is structural
    rather than a re-measurement.
    """
    readable: list[str] = []
    for path, scope in _projecting_scopes():
        if _delegates_to_resolver(path):
            continue
        readable.extend(_readable_binder_sites_in(path, scope))
    return readable


def _delegated_binder_sites() -> list[str]:
    """Projecting bodies whose binder call is the SDK's, not their own.

    **Returns nothing unless the SDK's own call can be read.** The credit is
    for delegating to a resolver that binds; if
    :func:`_canonical_binder_ownership` comes back empty the delegation is to
    a resolver that does not, and crediting it would convert the deletion of
    `D-IMPL-300`'s repair into a silently green floor.
    """
    if not _canonical_binder_ownership():
        return []
    return [
        f"{path.relative_to(REPO_ROOT)}:{_scope_line(scope)}"
        for path, scope in _projecting_scopes()
        if _delegates_to_resolver(path)
    ]


def test_the_binder_argument_scan_is_not_vacuous() -> None:
    """The argument checks are handed something to compare — a count over the tree.

    The two coverage floors say bodies were *found*. This one says the checks
    that read the binder's arguments were handed something to compare. A check
    that matched every body and could resolve none of their plans would report
    zero problems forever — CR-03's failure mode restated one layer in.

    **This assertion is a total, and a total is not a per-site property** — the
    distinction WR-F3 drew, and the reason its companion below exists. The two
    counts stand today at thirteen projecting bodies and twelve readable sites,
    so any body that gains a readable site while another loses one leaves this
    green. Keep both: this one catches a site disappearing from the tree, and
    :func:`test_every_bound_body_has_a_readable_plan_source` catches a body
    whose own plan the checks cannot read. Neither statement implies the other.
    """
    found = _resolved_binder_sites()
    assert len(found) >= MINIMUM_RESOLVED_BINDER_SITES, (
        f"{len(found)} binder call sites with a readable plan source,"
        f" {MINIMUM_RESOLVED_BINDER_SITES} expected."
        f" {FLOOR_REMOVAL_INSTRUCTION} Found: {found}"
    )


def test_the_canonical_path_binds_before_it_executes() -> None:
    """`D-IMPL-300`, read off the shipped resolver rather than trusted.

    The whole of :func:`_delegated_binder_sites` rests on this: an example that
    hands plan construction to
    :func:`~ccf.products.resolver.build_governed_resolver` is credited with a
    binder call it does not make, and that credit is only honest while the
    resolver actually makes one — **before** the projection runs, on the very
    plan object it then executes.

    Asserting presence alone would not be enough. The binder's job is to refuse
    an assembly that should never happen, so a call moved to *after* execution
    would still be present, still be found by a grep, and still be useless:
    gate 2 already catches divergence once the product exists. The ordering is
    the property, and the ordering is what is measured.
    """
    owned = _canonical_binder_ownership()
    assert owned, (
        f"{CANONICAL_BINDER_MODULE} no longer binds the plan it executes before"
        f" executing it. `{BINDER_CALL}` must be called with the same plan"
        " object subsequently handed to `execute(plan=...)`, at a lower line"
        " (`D-IMPL-300`). Every delegated binder site stops counting while this"
        " is false, so do not repair one by lowering the other."
    )


def test_the_delegated_binder_scan_is_not_vacuous() -> None:
    """The other half of the split (`D-IMPL-307`).

    Its companion above counts deployments that bind for themselves. This one
    counts deployments whose binder call is the SDK's, and the two together are
    what let a migration be read correctly: an example moving from one
    architecture to the other **decrements one floor and increments this one**,
    in the same commit. A lone decrement is a deployment that stopped binding
    and told nobody, which is exactly what a single total could not distinguish
    from a deployment that had adopted the resolver.

    Floors, not equalities, in both directions — but each sits at its observed
    count with no headroom, for the reason
    :func:`test_the_binder_scan_is_not_vacuous` gives.
    """
    found = _delegated_binder_sites()
    assert len(found) >= MINIMUM_DELEGATED_BINDER_SITES, (
        f"{len(found)} projecting bodies delegate binding to the governed"
        f" resolver, {MINIMUM_DELEGATED_BINDER_SITES} expected."
        f" {FLOOR_REMOVAL_INSTRUCTION} Found: {found}."
        " If this dropped to zero while"
        " `test_the_canonical_path_binds_before_it_executes` is also red, fix"
        " that one first — this floor is downstream of it by construction."
    )


@pytest.mark.parametrize(
    ("path", "scope"),
    _projecting_scopes(),
    ids=lambda value: (
        str(value.relative_to(REPO_ROOT)) if isinstance(value, pathlib.Path) else ""
    ),
)
def test_every_bound_body_has_a_readable_plan_source(
    path: pathlib.Path, scope: ast.AST
) -> None:
    """WR-F3: the per-site property the aggregate floor cannot express.

    A body can name the binder, be ordered correctly, run the plan it bound —
    and hand the binder a plan whose ``required=`` this module cannot read, at
    which point property (1) runs and says nothing. The aggregate floor above
    does not see that: the new body contributes zero readable sites while the
    existing twelve still contribute twelve, and ``12 >= 12`` holds. Both CR-F1
    and WR-F1 exploit exactly that arithmetic.

    **Per call, not per body (WR-02).** The first version of this assertion was
    ``any(...)``, which composes the same arithmetic one level down: a body with
    one compliant readable site absorbs any number of unreadable ones beside it,
    so a plan class this module does not recognise routes around property (1)
    while this assertion stays green. Measured over the tree, ``all()`` costs
    nothing today — thirteen projecting bodies, twelve binder calls, **zero**
    unreadable — and it is what makes the residual loud for the body that
    acquires it rather than for the body that acquires it *everywhere*.

    A body with no binder call at all takes the early exit below. The reason is
    not a general no-double-reporting principle — :func:`_binder_collapses`'s
    property (3) reports such a body too, deliberately (IN-03) — but that *this*
    assertion's message would be **vacuous** for it: "every call was handed an
    unreadable plan" names no line and describes nothing when there are no
    calls. Its failure is
    :func:`test_every_projecting_example_body_names_the_binder`'s.
    """
    bindings = _bindings(scope)
    sources = _plan_sources(scope, bindings)
    calls = _binder_calls(scope, bindings)
    if not calls:
        return
    unreadable = [
        call.lineno
        for call in calls
        if _handed_plan_source(call, sources, bindings) is None
    ]
    assert not unreadable, (
        f"{path.relative_to(REPO_ROOT)}:{_scope_line(scope)}:"
        f" {_scope_label(scope)} calls `{BINDER_CALL}` at line(s)"
        f" {', '.join(str(line) for line in unreadable)}, each handed a plan"
        f" whose `{PLAN_REQUIRED_KEYWORD}=` this module cannot read — a helper's"
        " return value, a subscript, a comprehension, a tuple element or a"
        " dynamic attribute. The argument check then ran over that call and"
        " could say nothing, which is `CR-03`'s failure mode one layer in."
        f" Build the plan in this body from a named local —"
        f" `{PLAN_REQUIRED_KEYWORD}=requirements.required_operator_keys` — so"
        " the two documents are two readable paths. A sibling call in this body"
        " that IS readable does not answer for this one: that composition was"
        " WR-02."
    )


@pytest.mark.parametrize(
    ("path", "scope"),
    _projecting_scopes(),
    ids=lambda value: (
        str(value.relative_to(REPO_ROOT)) if isinstance(value, pathlib.Path) else ""
    ),
)
def test_no_projecting_body_names_the_binder_without_binding_it(
    path: pathlib.Path, scope: ast.AST
) -> None:
    """CR-03: the binder is *doing something* here, not merely spelled here.

    The companion to
    :func:`test_every_projecting_example_body_names_the_binder`. That one is
    coverage — the binder appears. This one reads the call: its two arguments
    are two documents, the plan it was handed is the plan the engine runs, and
    it runs before the engine does.
    """
    problems = _binder_collapses(scope, path)
    assert not problems, "\n".join(problems)


def test_the_binder_argument_checks_reject_a_binder_that_cannot_fail() -> None:
    """Watched to bite, and watched to stay quiet — CR-03's own two variants.

    Every ``caught`` body below **passes** the coverage assertion: each one
    names the binder. That is the point. Before this check they were admitted
    outright, and the first of them is the one CR-03 leads with — a plan built
    from the claim it is about to be compared against, so ``claimed ==
    required`` holds unconditionally at
    ``refuse_operator_set_divergence``'s comparison.

    The ``benign`` bodies are the shapes this phase already established as
    correct, and a naive tightening breaks two of them: the replay
    environments' ``resolve_plan`` methods construct a plan, bind it and
    **return** it, with the engine call happening later inside
    ``ccf.replay.engine.replay``. Requiring an ``execute`` in the same body
    would be red on both, and they are asserted quiet here for that reason.
    """
    inline_claim = f"{BINDER_DECLARED_KEYWORD}.required_operator_keys"
    from_artifact = "requirements.required_operator_keys"

    def plan_of(source: str, name: str = "Fixture") -> str:
        return f"{name}{PLAN_CLASS_SUFFIX}(plan_id=pid, {PLAN_REQUIRED_KEYWORD}={source})"

    execute = f"ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)"
    bind = f"{BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared, {ENGINE_PLAN_KEYWORD}=plan)"

    caught = (
        # CR-03 variant 1 — the plan is built FROM the claim, so the binder
        # compares a value against itself and cannot fail
        "def serve(pid, r, declared):\n"
        f"    plan = {plan_of(inline_claim)}\n"
        f"    {bind}\n"
        f"    return {execute}\n",
        # the same, one alias hop between the claim and the plan
        "def serve(pid, r, declared):\n"
        f"    claim = {inline_claim}\n"
        f"    plan = {plan_of('claim')}\n"
        f"    {bind}\n"
        f"    return {execute}\n",
        # the same, with a transparent conversion in the way
        "def serve(pid, r, declared):\n"
        f"    plan = {plan_of(f'tuple({inline_claim})')}\n"
        f"    {bind}\n"
        f"    return {execute}\n",
        # the same at the replay shape, where `declared` is an attribute
        "def resolve_plan(self, pid):\n"
        f"    plan = {plan_of('self._declared.required_operator_keys')}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=self._declared,"
        f" {ENGINE_PLAN_KEYWORD}=plan)\n"
        "    return plan\n",
        # CR-03 variant 2 — the binder is handed a DIFFERENT plan than the one
        # the engine runs, so the plan that assembles the product is unbound
        "def serve(pid, r, declared, requirements):\n"
        f"    other = {plan_of(from_artifact)}\n"
        f"    plan = {plan_of(from_artifact)}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=other)\n"
        f"    return {execute}\n",
        # the binder runs AFTER the engine, so a product is already assembled
        # from a set the claim may contradict
        "def serve(pid, r, declared, requirements):\n"
        f"    plan = {plan_of(from_artifact)}\n"
        f"    out = {execute}\n"
        f"    {bind}\n"
        "    return out\n",
        # the plan is never hoisted: it comes into being inside the call
        # expression that consumes it, so no binder can have been handed it
        "def serve(pid, r, declared, requirements):\n"
        f"    spare = {plan_of(from_artifact)}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=spare)\n"
        "    return ProjectionEngine(reader=r).execute("
        f"{ENGINE_PLAN_KEYWORD}={plan_of(from_artifact)})\n",
        # CR-F1 — the identical collapse, spelled with a plan class the
        # Protocol does not require to be named `*Plan`. `ProjectionPlan` is
        # structural by commitment ("no base class to inherit and no registry
        # decorator to remember"), so a rename is a legal spelling of a
        # projection and cannot be a way out of the check written to close
        # CR-03. Before the rekey every assertion in this module passed on this
        # body while the binder compared a value against itself.
        "def serve(pid, r, declared):\n"
        f"    projection = CreditProjection({PLAN_ID_KEYWORD}=pid,"
        f" {PLAN_REQUIRED_KEYWORD}={inline_claim})\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=projection)\n"
        "    return ProjectionEngine(reader=r).execute("
        f"{ENGINE_PLAN_KEYWORD}=projection)\n",
        # the CR-03 variant 2 shape at one NAME rather than two (WR-F2): the
        # plan local is rebound between the bind and the second execution, so
        # the binder never saw the object that execution runs. A plan map keyed
        # on the name alone had one entry for the two constructions and
        # admitted this.
        "def serve(pid, r, declared, requirements):\n"
        f"    plan = {plan_of(from_artifact)}\n"
        f"    {bind}\n"
        f"    first = {execute}\n"
        f"    plan = {plan_of('whatever_i_like(declared)')}\n"
        f"    second = {execute}\n"
        "    return (first, second)\n",
    )
    for source in caught:
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        # every one of these satisfies the COVERAGE half — that is the finding
        assert _names_the_binder(function), source
        assert _binder_collapses(function, REPO_ROOT / "probe.py"), source

    benign = (
        # the compliant shape at ten of the eleven executing sites — the plan
        # reads the projection's own artifact, the binder reads the product
        # class's claim. The eleventh,
        # `examples/s1-00-companies-over-revenue/produce.py`, executes and makes
        # no binder call: it is the D-IMPL-137 one-document deployment, so this
        # shape is not what it is held to.
        "def serve(pid, r, declared, requirements):\n"
        f"    plan = {plan_of(from_artifact)}\n"
        f"    {bind}\n"
        f"    return {execute}\n",
        # the replay shape, done right — plan, bind, return; no engine here.
        # `self._requirements` and `self._declared` share a ROOT and are two
        # documents, which is why paths rather than roots are compared.
        "def resolve_plan(self, pid):\n"
        f"    plan = {plan_of('self._requirements.required_operator_keys')}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=self._declared,"
        f" {ENGINE_PLAN_KEYWORD}=plan)\n"
        "    return plan\n",
        # two projections in one body, each bound before its own execution
        "def serve(pid, r, declared, requirements):\n"
        f"    a = {plan_of(from_artifact)}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=a)\n"
        f"    first = ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=a)\n"
        f"    b = {plan_of(from_artifact)}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=b)\n"
        "    return (first, ProjectionEngine(reader=r).execute("
        f"{ENGINE_PLAN_KEYWORD}=b))\n",
        # the same local rebound, done RIGHT: each construction gets its own
        # binder call before its own execution. The rebinding is not the
        # defect — an unbound second object is — so this must stay quiet.
        "def serve(pid, r, declared, requirements):\n"
        f"    plan = {plan_of(from_artifact)}\n"
        f"    {bind}\n"
        f"    first = {execute}\n"
        f"    plan = {plan_of(from_artifact)}\n"
        f"    {bind}\n"
        f"    second = {execute}\n"
        "    return (first, second)\n",
        # the CR-F1 spelling of the COMPLIANT shape: a plan class named
        # anything, built from the projection's own artifact
        "def serve(pid, r, declared, requirements):\n"
        f"    projection = CreditProjection({PLAN_ID_KEYWORD}=pid,"
        f" {PLAN_REQUIRED_KEYWORD}={from_artifact})\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=projection)\n"
        "    return ProjectionEngine(reader=r).execute("
        f"{ENGINE_PLAN_KEYWORD}=projection)\n",
        # a workflow execution is not a projection and carries no binder
        "def drive(engine, workflow, execution_id):\n"
        "    return engine.execute(workflow, execution_id=execution_id)\n",
    )
    for source in benign:
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _binder_collapses(function, REPO_ROOT / "probe.py"), source


def test_every_binding_form_binds_and_the_unreadable_ones_say_so() -> None:
    """CR-01, at the helper that carries it — the enumeration, asserted.

    The predecessor read three forms and bound **nothing** for the rest, while
    :func:`_bindings`'s docstring said "every assignment to every local name".
    Each row below is a legal spelling of "this name is something else now", and
    a skipped one leaves the previous binding in force — which is worse than an
    unreadable one, because the checks then answer *affirmatively* about an
    object the name no longer holds.

    Both directions are asserted: the forms that bind, and the two that do not
    (a bare annotation, and a target that is an attribute or a subscript rather
    than a local name).

    **Binding is necessary and is not sufficient**, which is R4-CR-01 in one
    sentence: the round that added this enumeration left the *consumer*
    line-granular, so nine of these forms bound correctly and were then read at
    a position their own binding was not "before". What this test does not
    assert, and cannot, is that each binding is in force where Python puts it —
    that is a property of :func:`_binding_before` and it is asserted at the
    shipped checks, in
    :func:`test_a_rebinding_on_the_statements_own_line_is_seen` and
    :func:`test_a_plan_local_rebound_by_any_binding_form_is_seen`. The
    position assertion below is the narrow half of it: a binding whose position
    degrades to the body's own start sorts before every read in that body and is
    therefore never in force at all.
    """
    binds_unreadably = {
        "tuple unpack": "def f(x):\n    a, b = x.k, None\n",
        "list unpack": "def f(x):\n    [a, b] = x.k\n",
        "starred unpack": "def f(x):\n    a, *b = x.k\n",
        "nested unpack": "def f(x):\n    a, (b, c) = x.k\n",
        "aug assign": "def f(x):\n    a = 1\n    a += x.k\n",
        "for target": "def f(xs):\n    for a in xs:\n        pass\n",
        "async for target": "async def f(xs):\n    async for a in xs:\n        pass\n",
        "with as": "def f(cm):\n    with cm as a:\n        pass\n",
        "async with as": "async def f(cm):\n    async with cm as a:\n        pass\n",
        "except as": (
            "def f():\n    try:\n        pass\n    except ValueError as a:\n"
            "        pass\n"
        ),
        "import": "def f():\n    import a\n",
        "import dotted": "def f():\n    import a.b\n",
        "import from as": "def f():\n    from m import x as a\n",
        "nested def": "def f():\n    def a():\n        pass\n",
        "nested class": "def f():\n    class a:\n        pass\n",
        "match capture": "def f(x):\n    match x:\n        case [a]:\n            pass\n",
        "match star": "def f(x):\n    match x:\n        case [*a]:\n            pass\n",
        "match rest": (
            "def f(x):\n    match x:\n        case {'k': 1, **a}:\n            pass\n"
        ),
        "comprehension target": "def f(xs):\n    return [a for a in xs]\n",
    }
    for label, source in binds_unreadably.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef)
        bindings = _bindings(function)
        assert "a" in bindings, f"{label} bound nothing: {source}"
        assert all(binding.path is None for binding in bindings["a"]), label
        assert all(
            binding.position > _at(function) for binding in bindings["a"]
        ), (
            f"{label} recorded a binding at or before the body's own start,"
            " which sorts before every read in it and is therefore never in"
            " force — the trap `ast.withitem` sets, since it carries no"
            " position of its own and a missing one degrades to (0, 0). The"
            " position is taken from the item's CONTEXT EXPRESSION, which has"
            f" one. Observed: {bindings['a']}"
        )

    binds_readably = {
        "assign": "def f(x):\n    a = x.k\n",
        "chained assign": "def f(x):\n    a = b = x.k\n",
        "annotated assign": "def f(x):\n    a: int = x.k\n",
        "walrus": "def f(x):\n    print(a := x.k)\n",
    }
    for label, source in binds_readably.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert _bindings(function)["a"][0].path == ("x", "k"), label

    binds_nothing = {
        # a bare annotation is not a binding, and Python agrees
        "bare annotation": "def f(x):\n    a: int\n",
        # these bind a MEMBER, not a local name — the map is keyed by name, so a
        # read of `o.a` resolves to the literal path rather than to a stale value
        "attribute target": "def f(x, o):\n    o.a = x.k\n",
        "subscript target": "def f(x, d):\n    d['a'] = x.k\n",
        # `global` redirects where an assignment lands; it does not bind
        "global declaration": "def f():\n    global a\n",
    }
    for label, source in binds_nothing.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert "a" not in _bindings(function), label


def test_a_plan_local_rebound_by_any_binding_form_is_seen() -> None:
    """CR-01: every spelling of a rebinding, driven through the shipped checks.

    The reviewer's reproduction is the first row and it is the whole finding: a
    plan built from the binder's own ``declared=`` (CR-03 variant 1) which no
    binder was ever handed (CR-03 variant 2), rebound onto a name the binder
    *had* been handed by a **tuple** target. Every assertion in this module
    passed on it, because the tuple bound nothing and the second execution
    resolved to the first construction.

    The remaining rows are the same rebinding in the other spellings. Each is
    ordinary Python, and each was silent.
    """
    plan = f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid, {PLAN_REQUIRED_KEYWORD}=keys)"
    bind = f"{BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared, {ENGINE_PLAN_KEYWORD}=plan)"
    run = f"ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)"
    head = (
        "def serve(pid, keys, r, declared, alts, cm):\n"
        f"    plan = {plan}\n"
        f"    {bind}\n"
    )
    ahead = "async " + head

    rebound = {
        # the reviewer's own body: tuple target, second construction built FROM
        # `declared`, handed to no binder, and run by the engine
        "tuple target": (
            "def serve(pid, keys, r, declared):\n"
            f"    plan = {plan}\n"
            f"    {bind}\n"
            f"    first = {run}\n"
            f"    plan, spare = Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid,"
            f" {PLAN_REQUIRED_KEYWORD}={BINDER_DECLARED_KEYWORD}"
            ".required_operator_keys), None\n"
            f"    second = {run}\n"
            "    return (first, second)\n"
        ),
        "for target": head + f"    for plan in alts:\n        out = {run}\n    return out\n",
        "async for target": ahead
        + f"    async for plan in alts:\n        out = {run}\n    return out\n",
        "with as": head + f"    with cm as plan:\n        out = {run}\n    return out\n",
        "async with as": ahead
        + f"    async with cm as plan:\n        out = {run}\n    return out\n",
        "except as": head
        + "    try:\n        pass\n    except ValueError as plan:\n"
        + f"        out = {run}\n    return out\n",
        "tuple unpack": head + f"    plan, spare = alts\n    return {run}\n",
        "aug assign": head + f"    plan += alts\n    return {run}\n",
        "match capture": head
        + f"    match alts:\n        case [plan]:\n            out = {run}\n    return out\n",
        "import": head + f"    from elsewhere import plan\n    return {run}\n",
        "comprehension target": head + f"    return [{run} for plan in alts]\n",
    }
    for label, source in rebound.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef)
        # every one satisfies the COVERAGE half — that is the finding, again
        assert _names_the_binder(function), label
        assert _binder_collapses(function, REPO_ROOT / "probe.py"), (
            f"{label} is silent: {source}"
        )

    # …and the two shapes a rebinding must NOT be confused with. A comprehension
    # target does not escape the comprehension in Python 3, so the plan bound
    # before it is still the plan after it; and a rebinding with its own binder
    # is the compliant two-projection body, not a defect.
    quiet = {
        "comprehension does not leak": (
            head
            + "    labels = [str(plan) for plan in alts]\n"
            + f"    return (labels, {run})\n"
        ),
        # the same, with the comprehension and the execute on ONE line. This is
        # R4-WR-01's reproduction verbatim, and it is the shape that separates
        # a lexical span from a line range: the `plan` the engine runs is the
        # OUTER one, the comprehension's target does not leak, and the body is
        # correct. A line-ranged `until` put the comprehension's target in force
        # for every read on the line it spanned and reported this red.
        "comprehension does not leak, one line": (
            head + f"    return ([str(plan) for plan in alts], {run})\n"
        ),
        "rebound and bound again": (
            head + f"    first = {run}\n    plan = {plan}\n    {bind}\n"
            f"    second = {run}\n    return (first, second)\n"
        ),
    }
    for label, source in quiet.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _binder_collapses(function, REPO_ROOT / "probe.py"), (
            f"{label} is red on correct code: {source}"
        )


def test_a_rebinding_on_the_statements_own_line_is_seen() -> None:
    """R4-CR-01: the nine spellings the round before recorded and then discarded.

    :func:`_binding_records` read every binding *form*; ``_binding_before``
    consumed them with a strictly-below **line** comparison. A compound
    statement's binding is at the statement, so a suite written on that same
    line read the name at a line the binding was not yet "before" — and the
    **previous** binding answered, affirmatively, about an object the name no
    longer held. That is CR-01's own inversion one layer down, and it was
    reached by ordinary Python: ``for plan in alts: out = engine.execute(
    plan=plan)`` runs every plan in ``alts`` and the binder saw none of them.

    The three semicolon rows are the same failure without a compound statement.
    They are here because the fourth review measured them as **not** closed by
    the remedy it proposed (inclusive-from-the-statement's-own-line) and said
    so; a position-ordered consumer closes them, which is why the remedy
    adopted is the one that orders ``(line, column)`` rather than the one that
    was proposed.

    Every row satisfies the coverage half — that is the finding, for the third
    time in this phase. The quiet rows below are the two directions this must
    not have bought: correct code written on one line, and a compound
    statement's **header** reading the name it is about to rebind.
    """
    plan = f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid, {PLAN_REQUIRED_KEYWORD}=keys)"
    from_declared = (
        f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid,"
        f" {PLAN_REQUIRED_KEYWORD}={BINDER_DECLARED_KEYWORD}.required_operator_keys)"
    )
    bind = f"{BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared, {ENGINE_PLAN_KEYWORD}=plan)"
    run = f"ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)"
    head = (
        "def serve(pid, keys, r, declared, alts, cm):\n"
        f"    plan = {plan}\n"
        f"    {bind}\n"
    )
    ahead = "async " + head

    rebound = {
        "for, one-line suite": head
        + f"    for plan in alts: out = {run}\n    return out\n",
        "async for, one-line suite": ahead
        + f"    async for plan in alts: out = {run}\n    return out\n",
        "with as, one-line suite": head
        + f"    with cm as plan: out = {run}\n    return out\n",
        "async with as, one-line suite": ahead
        + f"    async with cm as plan: out = {run}\n    return out\n",
        "except as, one-line suite": head
        + "    try:\n        pass\n    except ValueError as plan: out = "
        + run
        + "\n    return out\n",
        "match capture, one-line suite": head
        + f"    match alts:\n        case [plan]: out = {run}\n    return out\n",
        "semicolon assign": head
        + f"    plan = {from_declared}; out = {run}\n    return out\n",
        "semicolon tuple": head
        + f"    plan, spare = {from_declared}, None; out = {run}\n    return out\n",
        "semicolon import": head
        + f"    from elsewhere import plan; out = {run}\n    return out\n",
    }
    for label, source in rebound.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef)
        assert _names_the_binder(function), label
        assert _binder_collapses(function, REPO_ROOT / "probe.py"), (
            f"{label} is silent: {source}"
        )

    quiet = {
        # the whole compliant body on one physical line. A line-ordered property
        # (3) reported this red — `call.lineno < first_execution` is false when
        # the two share a line — and property (2) reported it red beside it. Two
        # false positives on correct code, from the same comparison.
        "the compliant body, one line": (
            "def serve(pid, keys, r, declared):\n"
            f"    plan = {plan}; {bind}; out = {run}\n"
            "    return out\n"
        ),
        # a `for` header that READS the plan it is about to rebind. Python
        # evaluates the iterable before it binds the target, so this read is the
        # PREVIOUS plan — which is why the binding is anchored past the iterable
        # rather than at the `for` keyword. The remedy the fourth review
        # proposed got this one wrong and said so; this one does not.
        "a for header reading the name it rebinds": (
            "def serve(pid, keys, r, declared, transform):\n"
            f"    plan = {plan}\n"
            f"    {bind}\n"
            f"    out = {run}\n"
            "    for plan in transform(plan):\n"
            "        pass\n"
            "    return out\n"
        ),
        # the same for `with`, whose context expression is evaluated first
        "a with header reading the name it rebinds": (
            "def serve(pid, keys, r, declared, make):\n"
            f"    plan = {plan}\n"
            f"    {bind}\n"
            f"    out = {run}\n"
            "    with make(plan) as plan:\n"
            "        pass\n"
            "    return out\n"
        ),
        # a multi-line right-hand side that reads the name it binds. Anchoring
        # the binding at the STATEMENT put it in force over lines 3 and 4 of its
        # own value expression, so `required=plan...` resolved to the plan the
        # value was still computing.
        "a multi-line value reading the name it binds": (
            "def serve(pid, r, declared, requirements, plan):\n"
            f"    plan = Fixture{PLAN_CLASS_SUFFIX}(\n"
            "        plan_id=pid,\n"
            f"        {PLAN_REQUIRED_KEYWORD}=requirements.required_operator_keys,\n"
            "    )\n"
            f"    {bind}\n"
            f"    return {run}\n"
        ),
    }
    for label, source in quiet.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _binder_collapses(function, REPO_ROOT / "probe.py"), (
            f"{label} is RED on correct code: {source}"
        )

    # …and the ordering property still bites on one line, in the other
    # direction: the binder written AFTER the engine on the same line is the
    # shape property (3) exists for, and a position comparison is what lets it
    # say so without also refusing the compliant one-liner above.
    out_of_order = (
        "def serve(pid, keys, r, declared):\n"
        f"    plan = {plan}; out = {run}; {bind}\n"
        "    return out\n"
    )
    function = ast.parse(out_of_order).body[0]
    assert isinstance(function, ast.FunctionDef)
    assert _binder_collapses(function, REPO_ROOT / "probe.py"), out_of_order


def test_a_comprehension_binds_only_inside_its_own_lexical_span() -> None:
    """R4-WR-01: the target is scoped to the expression, not to the lines it spans.

    A comprehension target does not leak in Python 3, and the round before this
    one modelled that with the comprehension's first and last **line numbers**.
    Any other expression sharing one of those lines then had its reads
    attributed to the comprehension's target. Both directions were measured, and
    both are held here:

    * **red on correct code** — the reviewer's own body, which the predecessor
      at ``6cf00d3`` returned zero problems on. The ``plan`` the engine runs is
      the outer one; the body is correct and was reported unbound.
    * **quiet on a genuine collapse** — a comprehension binding ``ops`` on the
      gate call's own line resolved the gate's read to the comprehension's
      opaque token, so tripwire (1) compared two different sources and said
      nothing about a body whose two sides are the same value.

    The last two rows are the properties this must not have cost: a read
    genuinely *inside* the comprehension still resolves to the comprehension's
    own target, and an ordinary rebinding written after the comprehension is
    still a rebinding.
    """
    plan = f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid, {PLAN_REQUIRED_KEYWORD}=keys)"
    bind = f"{BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared, {ENGINE_PLAN_KEYWORD}=plan)"
    run = f"ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)"
    head = (
        "def serve(pid, keys, r, declared, alts):\n"
        f"    plan = {plan}\n"
        f"    {bind}\n"
    )

    correct = {
        # R4-WR-01's reproduction, verbatim
        "list comprehension beside the execute": head
        + f"    return ([str(plan) for plan in alts], {run})\n",
        # not confined to one-liners: any outer read landing on a line the
        # comprehension spans triggered it
        "comprehension spanning the execute's line": head
        + "    return combine([x\n"
        + f"        for plan in alts], {run})\n",
        # a generator expression measures identically
        "generator expression beside the execute": head
        + f"    return (tuple(str(plan) for plan in alts), {run})\n",
        # and a set and a dict comprehension, for the two node types the
        # enumeration in `_binding_records` covers but no probe reached
        "set comprehension beside the execute": head
        + f"    return ({{str(plan) for plan in alts}}, {run})\n",
        "dict comprehension beside the execute": head
        + f"    return ({{plan: 1 for plan in alts}}, {run})\n",
    }
    for label, source in correct.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _binder_collapses(function, REPO_ROOT / "probe.py"), (
            f"{label} is RED on correct code: {source}"
        )

    # the tripwire (1) mirror: both sides read `ops`, and a comprehension on the
    # gate call's own line shadowed the name into silence
    collapse = (
        "def serve(candidate, declared, xs):\n"
        f"    ops = frozenset({BINDER_DECLARED_KEYWORD}.required_operator_keys)\n"
        f"    product = {LINEAGE_CONSTRUCTOR}({LINEAGE_DECLARED_KEYWORD}=ops)\n"
        "    return ([f(ops) for ops in xs],"
        f" {GATE_CALL}(candidate, {GATE_RESOLVED_KEYWORD}=ops))\n"
    )
    function = ast.parse(collapse).body[0]
    assert isinstance(function, ast.FunctionDef)
    assert _gate_collapses(function, REPO_ROOT / "probe.py"), collapse

    # a read genuinely INSIDE the comprehension is still the comprehension's own
    # target, so the execute spelled inside one is still unbound
    inside = head + f"    return [{run} for plan in alts]\n"
    function = ast.parse(inside).body[0]
    assert isinstance(function, ast.FunctionDef)
    assert _binder_collapses(function, REPO_ROOT / "probe.py"), inside

    # and a genuine rebinding after the comprehension is still a rebinding: the
    # comprehension is not a licence for what follows it
    after = (
        head
        + "    labels = [str(plan) for plan in alts]\n"
        + f"    plan = Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid,"
        f" {PLAN_REQUIRED_KEYWORD}={BINDER_DECLARED_KEYWORD}.required_operator_keys)\n"
        + f"    return (labels, {run})\n"
    )
    function = ast.parse(after).body[0]
    assert isinstance(function, ast.FunctionDef)
    assert _binder_collapses(function, REPO_ROOT / "probe.py"), after


def test_a_walrus_does_not_route_around_the_hoist_branch() -> None:
    """R4-WR-02: ``(plan := FooPlan(...))`` is the construction it evaluates to.

    Property (2)'s hoist branch fires on ``_is_plan_construction(plan_node)``.
    A walrus made ``plan_node`` an ``ast.NamedExpr`` rather than an ``ast.Call``,
    so the branch did not fire; ``_binding_path`` then yielded ``None`` for the
    same node and the execution took the ``execution.plan is None`` quiet exit.
    The module had already recorded the construction's source and was holding it
    — so this was never the "no identifier path" limit the docstring claimed, it
    was a path the module had and did not consult.

    Both sides of the binder seam are asserted, because the same unwrapping
    decides both: the *execution* side takes the hoist branch, and the *binder*
    side becomes readable, which is what lets property (1) speak about it at
    all.
    """
    inline = (
        f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid,"
        f" {PLAN_REQUIRED_KEYWORD}={BINDER_DECLARED_KEYWORD}.required_operator_keys)"
    )
    compliant = (
        f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid,"
        f" {PLAN_REQUIRED_KEYWORD}=requirements.required_operator_keys)"
    )
    head = (
        "def serve(pid, r, declared, requirements):\n"
        f"    plan = {compliant}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=plan)\n"
    )

    # the execution side: the plan comes into being inside the call that
    # consumes it, walrus or no walrus
    walrus = head + (
        "    return ProjectionEngine(reader=r).execute("
        f"{ENGINE_PLAN_KEYWORD}=(plan := {inline}))\n"
    )
    without = head + (
        f"    return ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}={inline})\n"
    )
    for label, source in (("walrus", walrus), ("no walrus", without)):
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert _names_the_binder(function), label
        assert _binder_collapses(function, REPO_ROOT / "probe.py"), (
            f"{label} is silent: {source}"
        )

    # the binder side: a walrus-wrapped plan is READABLE, so the per-call
    # readable-source assertion is satisfied and property (1) can speak
    handed = (
        "def serve(pid, r, declared):\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=(plan := {inline}))\n"
        f"    return ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)\n"
    )
    function = ast.parse(handed).body[0]
    assert isinstance(function, ast.FunctionDef)
    bindings = _bindings(function)
    sources = _plan_sources(function, bindings)
    calls = _binder_calls(function, bindings)
    assert len(calls) == 1, handed
    assert _handed_plan_source(calls[0], sources, bindings) is not None, handed
    assert _binder_collapses(function, REPO_ROOT / "probe.py"), handed

    # …and the compliant walrus spelling stays quiet: the plan is hoisted into a
    # local by the walrus itself, bound, and then run
    quiet = (
        "def serve(pid, r, declared, requirements):\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=(plan := {compliant}))\n"
        f"    return ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)\n"
    )
    function = ast.parse(quiet).body[0]
    assert isinstance(function, ast.FunctionDef)
    assert not _binder_collapses(function, REPO_ROOT / "probe.py"), quiet


def test_a_loop_carried_rebinding_is_out_of_reach_and_says_so() -> None:
    """R4-WR-03: the limit, asserted as a limit rather than asserted away.

    A loop makes lines execute out of textual order. A plan rebuilt at the
    bottom of a loop body is in force at the top of that body on every iteration
    after the first, and a walk that answers "which binding is textually last
    before this position" reads it as never in force. The body below runs, from
    its second iteration on, a plan built from the binder's own ``declared=``
    that no binder was handed — and this module is **silent** on it.

    Asserting the silence is the point. A limit named in a docstring and not
    held by a test is a sentence that can quietly stop being true in either
    direction: if a later change closes this, the assertion fails and the limits
    list gets corrected in the same commit; if a later change makes it worse,
    nothing here moves and that is honest too. The companion assertion is the
    straight-line spelling, which **is** caught — so this is a statement about
    control flow and not about the check having gone quiet.

    Closing it needs control-flow ordering rather than lexical ordering, which
    is a different analysis from the one this module is. It is carried, not
    fixed.
    """
    compliant = (
        f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid,"
        f" {PLAN_REQUIRED_KEYWORD}=requirements.required_operator_keys)"
    )
    inline = (
        f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid,"
        f" {PLAN_REQUIRED_KEYWORD}={BINDER_DECLARED_KEYWORD}.required_operator_keys)"
    )
    run = f"ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=plan)"
    head = (
        "def serve(pid, r, declared, requirements, alts):\n"
        f"    plan = {compliant}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=plan)\n"
    )

    loop_carried = {
        "for": head
        + "    for item in alts:\n"
        + f"        out = {run}\n"
        + f"        plan = {inline}\n"
        + "    return out\n",
        "while": head
        + "    while alts:\n"
        + f"        out = {run}\n"
        + f"        plan = {inline}\n"
        + "    return out\n",
    }
    for label, source in loop_carried.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _binder_collapses(function, REPO_ROOT / "probe.py"), (
            f"{label} is no longer silent — R4-WR-03 has been closed, and the"
            " limits lists in this module's docstring and the phase SUMMARY"
            f" must be corrected in the same commit: {source}"
        )

    # the straight-line spelling of the identical rebinding IS caught, which is
    # what makes the silence above a control-flow statement rather than a hole
    straight_line = (
        head + f"    out = {run}\n    plan = {inline}\n    second = {run}\n"
        "    return (out, second)\n"
    )
    function = ast.parse(straight_line).body[0]
    assert isinstance(function, ast.FunctionDef)
    assert _binder_collapses(function, REPO_ROOT / "probe.py"), straight_line


def test_a_class_body_and_a_lambda_are_lexical_bodies() -> None:
    """R4-IN-01: ``_scopes``'s enumeration matches what ``_scope_nodes`` refuses.

    ``_scope_nodes`` deliberately stops at a ``ClassDef`` and a ``Lambda``, so a
    body ``_scopes`` does not list is scanned by **nothing**. A plan constructed
    in a class body was not "scanned and unresolvable" — a limit the docstring
    covers — it was invisible, and ``MINIMUM_PROJECTING_BODIES`` could not see
    it either, because the body never entered the count.

    Both halves are asserted: the bodies are enumerated, and the constructions
    inside them are reached. Measured before the widening: **zero** class bodies
    and **zero** lambda bodies under ``examples/`` construct or run a
    projection, and **zero** under the gate-scanned trees call ``run_gates``, so
    no floor and no verdict moved.
    """
    module = ast.parse(
        "class Deployment:\n"
        f"    plan = Fixture{PLAN_CLASS_SUFFIX}({PLAN_ID_KEYWORD}='p',"
        f" {PLAN_REQUIRED_KEYWORD}=declared.required_operator_keys)\n"
        "\n"
        f"make = lambda pid: Fixture{PLAN_CLASS_SUFFIX}({PLAN_ID_KEYWORD}=pid,"
        f" {PLAN_REQUIRED_KEYWORD}=declared.required_operator_keys)\n"
    )
    labels = {_scope_label(scope) for scope in _scopes(module)}
    assert "class Deployment" in labels, labels
    assert "<lambda>" in labels, labels

    reached = {
        _scope_label(scope)
        for scope in _scopes(module)
        for node in _scope_nodes(scope)
        if _is_plan_construction(node) or _is_plan_execution(node)
    }
    assert reached == {"class Deployment", "<lambda>"}, reached


def test_a_rebinding_is_two_sources_for_the_gate_tripwire_too() -> None:
    """CR-01's other consequence: tripwire (1) red on correct code, again.

    WR-F2(a)'s charter was exactly this body — a local reused for the claim and
    then for something else — and it was fixed for the one spelling ``ops = …``.
    Under every other spelling the second binding was invisible, both sides
    resolved to ``declared.required_operator_keys``, and this **correct** body
    was reported as the CR-2 collapse.

    The last row is the control: the genuine collapse must still be caught, so
    this is not the check going quiet.
    """
    engine = ".".join(("execution", LINEAGE_DECLARED_KEYWORD))
    claim = f"frozenset({BINDER_DECLARED_KEYWORD}.required_operator_keys)"
    head = (
        "def serve(execution, candidate, declared, pair, batches, cm):\n"
        f"    ops = {claim}\n"
        f"    product = {LINEAGE_CONSTRUCTOR}({LINEAGE_DECLARED_KEYWORD}=ops)\n"
    )
    tail = f"    return {GATE_CALL}(candidate, {GATE_RESOLVED_KEYWORD}=ops)\n"

    correct = {
        "tuple target": head + "    ops, spare = pair\n" + tail,
        "aug assign": head + f"    ops |= {engine}\n" + tail,
        "for target": head + "    for ops in batches:\n        pass\n" + tail,
        "with as": head + "    with cm as ops:\n        pass\n" + tail,
        "except as": head
        + "    try:\n        pass\n    except ValueError as ops:\n        pass\n"
        + tail,
    }
    for label, source in correct.items():
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _gate_collapses(function, REPO_ROOT / "probe.py"), (
            f"{label} is RED on correct code: {source}"
        )

    collapse = head + f"    return {GATE_CALL}(candidate, {GATE_RESOLVED_KEYWORD}={claim})\n"
    function = ast.parse(collapse).body[0]
    assert isinstance(function, ast.FunctionDef)
    assert _gate_collapses(function, REPO_ROOT / "probe.py"), collapse


def test_one_readable_binder_call_does_not_answer_for_an_unreadable_sibling() -> None:
    """WR-02: the per-call form of the readable-plan-source property.

    The body below has two binder calls. The first is compliant and readable.
    The second is handed a plan this module does not recognise as a plan
    construction — Protocol members inherited from a base class, no ``plan_id=``
    — and built from the binder's own ``declared=``, so property (1) is silent
    about it. Under ``any()`` the readable sibling absorbed it and every
    assertion in the module passed; the aggregate floor was unaffected too,
    because the body still contributes one readable site.

    Asserted through the same helpers
    :func:`test_every_bound_body_has_a_readable_plan_source` uses, so this is the
    assertion's own arithmetic rather than a restatement of it.
    """
    good = f"Fixture{PLAN_CLASS_SUFFIX}(plan_id=pid, {PLAN_REQUIRED_KEYWORD}=keys)"
    bad = (
        f"CreditProjection(identity=pid, operators={BINDER_DECLARED_KEYWORD}"
        ".required_operator_keys)"
    )
    source = (
        "def serve(pid, keys, r, declared):\n"
        f"    good = {good}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=good)\n"
        f"    first = ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=good)\n"
        f"    bad = {bad}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=bad)\n"
        f"    second = ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=bad)\n"
        "    return (first, second)\n"
    )
    function = ast.parse(source).body[0]
    assert isinstance(function, ast.FunctionDef)
    bindings = _bindings(function)
    sources = _plan_sources(function, bindings, frozenset())
    calls = _binder_calls(function, bindings)
    readable = [
        _handed_plan_source(call, sources, bindings, frozenset()) is not None
        for call in calls
    ]

    assert len(calls) == 2, source
    # the finding: one is readable, one is not, and `any()` reported the body as
    # covered — which is the composition WR-02 named
    assert any(readable), source
    assert not all(readable), source

    # and the compliant two-projection body, which `all()` must leave quiet
    compliant = (
        "def serve(pid, keys, r, declared):\n"
        f"    a = {good}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=a)\n"
        f"    first = ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=a)\n"
        f"    b = {good}\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=b)\n"
        f"    second = ProjectionEngine(reader=r).execute({ENGINE_PLAN_KEYWORD}=b)\n"
        "    return (first, second)\n"
    )
    function = ast.parse(compliant).body[0]
    assert isinstance(function, ast.FunctionDef)
    bindings = _bindings(function)
    sources = _plan_sources(function, bindings, frozenset())
    calls = _binder_calls(function, bindings)
    assert len(calls) == 2, compliant
    assert all(
        _handed_plan_source(call, sources, bindings, frozenset()) is not None
        for call in calls
    ), compliant


def test_a_plan_class_is_recognised_by_the_protocol_and_not_by_its_name() -> None:
    """CR-F1, at the branch that carries it — structural, like the Protocol.

    The rename probe in
    :func:`test_the_binder_argument_checks_reject_a_binder_that_cannot_fail`
    is caught by the ``plan_id=``/``required=`` keyword shape. That shape is a
    constructor convention, so on its own it would be the identical defect one
    step sideways: rename the *keyword* and the check goes quiet again.

    This holds the branch that answers the question the way
    ``ProjectionPlan`` answers it. The class below is named nothing like a
    plan, is constructed with a keyword the suite does not use, and exposes
    ``required_operators()`` and ``invoke()`` — which is the SDK's whole
    definition of "is a projection". Both halves are asserted: recognised with
    the module's class index, and *not* recognised without it, so the branch is
    demonstrably the one doing the work rather than a spare wheel.
    """
    module = ast.parse(
        "class CreditProjection:\n"
        "    def required_operators(self):\n"
        "        return self._required\n"
        "    def invoke(self, **kwargs):\n"
        "        return None\n"
        "\n"
        "def serve(pid, r, declared):\n"
        f"    projection = CreditProjection(identity=pid,"
        f" {PLAN_REQUIRED_KEYWORD}={BINDER_DECLARED_KEYWORD}"
        ".required_operator_keys)\n"
        f"    {BINDER_CALL}({BINDER_DECLARED_KEYWORD}=declared,"
        f" {ENGINE_PLAN_KEYWORD}=projection)\n"
        "    return ProjectionEngine(reader=r).execute("
        f"{ENGINE_PLAN_KEYWORD}=projection)\n"
    )
    classes = _plan_classes_in(module)
    assert "CreditProjection" in classes

    serve = module.body[1]
    assert isinstance(serve, ast.FunctionDef)
    constructions = [
        node
        for node in _scope_nodes(serve)
        if isinstance(node, ast.Call) and _callee(node) == "CreditProjection"
    ]
    assert len(constructions) == 1
    assert not _is_plan_construction(constructions[0], frozenset())
    assert _is_plan_construction(constructions[0], classes)

    assert _binder_collapses(serve, REPO_ROOT / "probe.py", classes)
    assert not _binder_collapses(serve, REPO_ROOT / "probe.py", frozenset())


def test_the_plan_recognition_refuses_an_unrelated_required_keyword() -> None:
    """The rekey is discriminating, and ``examples/`` is what proves it.

    The reviewed fix for CR-F1 proposed keying the plan-source map on the
    ``required=`` keyword alone. Measured across ``src/``, ``runtime/``,
    ``examples/`` and ``tests/`` that keyword appears on sixty-seven calls and
    fifty-three of them are ``argparse`` and other unrelated APIs — one of them
    inside ``examples/``, the tree this tripwire scans, where it would turn a
    command-line parser into a projecting body obliged to call the binder. A
    check red on correct code is the defect this whole cycle keeps producing,
    so the rekey requires ``plan_id=`` alongside it or a class the Protocol
    recognises.

    Asserted against the tree rather than only against a probe, because a probe
    proves the rule and the tree proves the rule was needed. If the last such
    call ever leaves ``examples/``, this fails loudly and can be retired
    deliberately — which is the right way round.

    **The evidence base was n = 1 when this was written; it is n = 2 today**
    (IN-02). Measured 2026-08-06: twelve calls under ``examples/`` pass
    ``required=``, eleven of them are plan constructions, and the twelfth is
    ``archive/examples/03-harness-portability/run.py::main``'s ``--mode``
    ``add_argument``. On that count, making that one CLI flag optional — or
    retiring example 03 — turned a ``tests/products/`` Gate-2 test red for a
    reason with nothing to do with Gate 2.

    **Re-measured 2026-08-15:** fifteen calls pass ``required=``, thirteen are
    plan constructions, and **two** are not — example 03's ``--mode`` and
    ``examples/s1-00-companies-over-revenue/consume.py::main``'s
    ``--min-revenue``, both ``argparse``. Retiring example 03 alone therefore no
    longer turns this red; the second site carries it. The trade above is
    unchanged and still deliberate — a loud, self-explaining failure beats the
    rule quietly ceasing to be demonstrated — but the count a reader is entitled
    to know is two, and the single-point-of-failure warning the original
    paragraph carried no longer holds. The dated measurement is kept rather than
    overwritten, per this module's practice of recording what changed.
    """
    unrelated: list[str] = []
    for path in _python_sources(BINDER_SCANNED_TREES):
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not any(
                keyword.arg == PLAN_REQUIRED_KEYWORD for keyword in node.keywords
            ):
                continue
            if _is_plan_construction(node):
                continue
            unrelated.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert unrelated, (
        f"no call under {BINDER_SCANNED_TREES} passes"
        f" `{PLAN_REQUIRED_KEYWORD}=` without being a plan construction, so"
        " this test no longer demonstrates that the keyword alone is not"
        " discriminating. Re-measure before concluding the rule can be"
        f" relaxed: `{PLAN_ID_KEYWORD}=` is what makes the pair specific."
    )


# --- termination ---------------------------------------------------------------


class _TookTooLong(Exception):
    """The body of :func:`_within` exceeded its wall-clock bound."""


@contextlib.contextmanager
def _within(seconds: float) -> Iterator[None]:
    """Bound a block by wall clock, so a regression fails instead of hanging.

    ``SIGALRM`` rather than a worker thread because the property under test is
    that a *loop* terminates: a thread that never returns cannot be joined and
    would leave the suite hanging in a different place, which is the failure
    mode being guarded against.
    """
    def _fire(signum: int, frame: types.FrameType | None) -> None:
        raise _TookTooLong

    previous = signal.signal(signal.SIGALRM, _fire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


@pytest.mark.skipif(
    not hasattr(signal, "SIGALRM"), reason="wall-clock bound needs POSIX SIGALRM"
)
def test_alias_resolution_terminates_on_a_cyclic_assignment_chain() -> None:
    """Resolution returns on a rotation instead of spinning forever.

    A three-name rotation is legal, executable Python — ``a`` takes ``b``'s
    value, ``b`` takes ``c``'s, ``c`` takes the old ``a`` — so the answer to it
    has to be a *result*, not a refusal; refusing would be red on correct code,
    which is the defect this module was separately found to have elsewhere.

    Two predecessors failed here in two different ways, and this test holds the
    property against both.

    The first grew a shared binding map to a fixed point and never reached one:
    ``a`` settled at ``(c,)``, ``c`` at ``(a,)``, and ``b`` alternated between
    the two forever. Since the scan runs over every ``.py`` file under ``src/``,
    ``runtime/`` and ``examples/``, one contributor writing that shape hung
    ``pytest`` with no output and no timeout to break it. The bound below is what
    makes a regression *fail* rather than hang.

    The second terminated but answered conservatively — each rotating name to
    itself, three sources where the code has two — and could only do that
    because it had no notion of *when* a name was bound. :func:`_resolve_at`
    resolves each hop as of the **position** that bound it, so the walk strictly
    ascends the body in the ``(line, column)`` order and terminates by
    construction, and the answer it terminates on is the one Python gives: at
    the bottom of the rotation ``a`` and ``c`` both hold the parameter ``b``, and
    ``b`` holds the parameter ``c``. The assertion below is therefore *stronger*
    than its predecessor's inequality, not weaker: it pins the semantics rather
    than the fallback.

    The comprehension probes at the end are where termination is least obvious,
    because containment is the one branch that can answer at a position the walk
    is already at. They also hold the lexical-span property itself: a read inside
    the comprehension, and a read on the same line but outside it, must get
    different answers.
    """
    rotation = ast.parse(
        "def f(b, c):\n"
        "    a = b\n"
        "    b = c\n"
        "    c = a\n"
        f"    return {GATE_CALL}(x, {GATE_RESOLVED_KEYWORD}=a)\n"
    ).body[0]
    assert isinstance(rotation, ast.FunctionDef)

    with _within(5.0):
        bindings = _bindings(rotation)
        # line 5 is the `return`, so every name is read at the bottom of the body
        resolved = {
            name: _resolve_at((name,), (5, 0), bindings) for name in ("a", "b", "c")
        }

    assert resolved == {"a": ("b",), "b": ("c",), "c": ("b",)}

    # The same shape with an attribute in the chain grew the path one element
    # per pass as well as never converging, so memory grew without bound.
    growing = ast.parse(
        "def f(b, c):\n"
        "    a = b.k\n"
        "    b = c.k\n"
        "    c = a.k\n"
        f"    return {GATE_CALL}(x, {GATE_RESOLVED_KEYWORD}=a)\n"
    ).body[0]
    assert isinstance(growing, ast.FunctionDef)
    with _within(5.0):
        grown = _bindings(growing)
        assert _resolve_at(("a",), (5, 0), grown) == ("b", "k")

    # A two-name cycle and a self-assignment were already survivable; they stay
    # so, and are asserted rather than assumed.
    for source, name in (
        ("def f(b):\n    a = b\n    b = a\n", "a"),
        ("def f(a):\n    a = a.k\n", "a"),
    ):
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        with _within(5.0):
            assert _resolve_at((name,), (99, 0), _bindings(function)) is not None

    # A comprehension binding is in force for reads LEXICALLY INSIDE it
    # (:func:`_binding_before`), which is the one place the walk could ask about
    # a position it is already at. It terminates because every such binding is
    # unreadable and :func:`_resolve_at` stops at an unreadable one — asserted
    # here rather than argued, over a comprehension that shadows the name it
    # reads and one that shadows a name bound above it.
    shadowing = ast.parse(
        "def f(xs, y):\n"
        "    a = y.k\n"
        "    b = [a for a in xs]\n"
        "    return a\n"
    ).body[0]
    assert isinstance(shadowing, ast.FunctionDef)
    with _within(5.0):
        shadow_bindings = _bindings(shadowing)
        # (3, 9) is the element expression `a`, inside the `[` at column 8
        inside = _resolve_at(("a",), (3, 9), shadow_bindings)
        after = _resolve_at(("a",), (4, 11), shadow_bindings)
    # inside the comprehension the name is the comprehension's own target, which
    # this module cannot read through; after it, the binding above is back in
    # force, because a comprehension target does not leak in Python 3
    assert inside == (_opaque("a", (3, 8)),)
    assert after == ("y", "k")

    # …and the same comprehension, read from a position on its own line but
    # OUTSIDE its span, resolves to the binding above it. A line-ranged `until`
    # answered this with the comprehension's target and was red on correct code
    # (R4-WR-01); lexical containment is what makes the two different questions.
    beside = ast.parse(
        "def f(xs, y):\n"
        "    a = y.k\n"
        "    b = ([a for a in xs], a)\n"
    ).body[0]
    assert isinstance(beside, ast.FunctionDef)
    with _within(5.0):
        beside_bindings = _bindings(beside)
        # (3, 10) is inside the comprehension; (3, 25) is the `a` beside it
        assert _resolve_at(("a",), (3, 10), beside_bindings) == (
            _opaque("a", (3, 9)),
        )
        assert _resolve_at(("a",), (3, 25), beside_bindings) == ("y", "k")


def test_the_wall_clock_bound_is_itself_live() -> None:
    """``_within`` fires — otherwise the termination test proves nothing.

    A bound that never triggers passes every body, including one that hangs.
    """
    with pytest.raises(_TookTooLong):
        with _within(0.05):
            while True:  # noqa: WPS457 - deliberately non-terminating
                pass
