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

**Following is line-aware, and that is a correctness property rather than a
refinement.** A name is resolved to the assignment in force *at the line that
reads it* (:func:`_binding_before`), so a body that reuses an ordinary local
name for two different values has two sources and not one. Its predecessor kept
one binding per name and was **red on correct code** for that reason (WR-F2).
The same model is what lets a binding this module cannot read through still be
a *source*: ``plan = QuickstartPlan(...)`` at line 231 is the token ``plan@231``
(:func:`_opaque`), so two reads of one construction share a source and two
constructions do not — which is object identity, and is what property (2) below
needs.

**Every binding form Python has is read, and the ones it cannot read through are
recorded as unreadable rather than skipped** (:func:`_binding_records`). That
distinction is CR-01, and it is not a refinement either: a *skipped* binding
leaves the previous one in force, so the checks go on describing an object the
name no longer holds — and answer **affirmatively**. A tuple unpack, a ``for``
target, a ``with … as``, an ``except … as``, an augmented assignment, a ``match``
capture, an import and a nested ``def``/``class`` each bound nothing under the
predecessor, and each of them is a legal spelling of "this name is something else
now". A comprehension's target binds too, and is scoped to the comprehension's
own lines, because in Python 3 it does not leak.

What tripwire (1) cannot catch — the structural limit, not a caution
---------------------------------------------------------------------

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

**Coverage.** Every lexical body under ``examples/`` that constructs a
projection plan, or runs one through ``ProjectionEngine(...).execute(...)``,
must **name** :func:`ccf.deployment.refuse_operator_set_divergence`.

**Arguments.** Naming it is not enough, and for one wave it was all that was
asked. A body can name the binder and route around it completely::

    plan = FooPlan(plan_id='p', required=declared.required_operator_keys)
    refuse_operator_set_divergence(declared=declared, plan=plan)
    return ProjectionEngine(reader=r).execute(plan=plan)

``plan.required_operators()`` is now ``declared.required_operator_keys``, so
``claimed == required`` holds unconditionally at ``binder.py:156-159``. The
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

``refuse_operator_set_divergence`` returns ``None`` by contract — deliberately,
so it can never grow into a helper that supplies one of Gate 2's arguments. The
consequence is that **nothing observable at runtime proves the call happened**:
no product field, no pin, no audit event. A deployment that omits it produces
output byte-identical to one that made it. An AST check is therefore the only
mechanism available, and this module claims exactly that and no more.

What tripwire (2) still cannot see
-----------------------------------

Named rather than implied away, and each one distinct from the authorship
residual below:

* **Reachability.** A binder call inside a never-taken ``if``, an ``except``
  handler or a ``# pragma: no cover`` branch is named, is ordered before the
  engine, and never runs. Ordering is readable from line numbers and is
  checked; reachability is not readable from an AST walk and is not.
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

Granularity is the **lexical body, not the file**. ``examples/06-decision-replay/run.py``
and ``examples/external/00-hello-context/run.py`` each carry two plan-construction
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

``SCANNED_TREES`` omits ``tests``, copying ``test_required_operators_guard.py:77-79``
and for its reason: a test may legitimately build a deliberately-tautological
construction in order to prove that a guard fires.
``tests/examples/test_gate_two_divergence.py`` — this plan's third module — is
one of the places that happens, and ``tests/products/test_gate_independence.py``
is another.
"""

from __future__ import annotations

import ast
import contextlib
import pathlib
import signal
import types
from collections.abc import Iterator
from typing import NamedTuple

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The trees a gate call site can live in. ``tests/`` is deliberately excluded
#: — see the docstring's closing section.
SCANNED_TREES: tuple[str, ...] = ("src", "runtime", "examples")

#: The trees the binder-coverage tripwire scans. ``examples/`` only, and the
#: docstring says why that is the honest scope rather than a shortfall.
BINDER_SCANNED_TREES: tuple[str, ...] = ("examples",)

#: The gate call and the keyword carrying the engine's side of Gate 2.
GATE_CALL = "run_gates"
GATE_RESOLVED_KEYWORD = "engine_resolved"

#: The lineage construction and the keyword carrying the product's side.
LINEAGE_CONSTRUCTOR = "ProductLineage"
LINEAGE_DECLARED_KEYWORD = "operators_invoked"

#: The binder every projecting body must name (D-IMPL-86 element (3), as
#: corrected 2026-08-05).
BINDER_CALL = "refuse_operator_set_divergence"

#: The binder's two keyword arguments. ``declared=`` carries the Control Plane
#: **claim**; ``plan=`` carries the plan whose ``required_operators()`` is
#: compared against it. Naming the binder is not enough — these two are what
#: has to arrive from two documents, and checking that is what turns tripwire
#: (2) from a spelling check into a check.
BINDER_DECLARED_KEYWORD = "declared"
BINDER_PLAN_KEYWORD = "plan"

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

#: The suite carries one gate call site per example that serves a product. A
#: scan that silently matched zero call sites is the quietest way a tripwire
#: stops being one, so the floor is asserted rather than assumed.
MINIMUM_GATE_CALL_SITES = 9

#: Nine bodies that construct a plan and execute it, plus the two replay
#: environments' ``resolve_plan`` methods, which construct one and return it.
#: Counted from the tree, not carried over from the plan text.
MINIMUM_PROJECTING_BODIES = 11

#: Binder call sites where this module can actually **read** which document the
#: handed plan's ``required=`` came from — the input the argument checks in
#: :func:`_binder_collapses` consume. The two coverage floors above say bodies
#: were found; this one says the argument checks were handed something to
#: compare. A tripwire matching bodies it can say nothing about is the CR-03
#: failure mode restated, so it is asserted rather than assumed.
MINIMUM_RESOLVED_BINDER_SITES = 11

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
    """Every lexical body in a module: the module itself, and each function."""
    bodies: list[ast.AST] = [tree]
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            bodies.append(node)
    return bodies


def _scope_label(scope: ast.AST) -> str:
    if isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef):
        return f"{scope.name}()"
    return "<module>"


def _scope_line(scope: ast.AST) -> int:
    return getattr(scope, "lineno", 1)


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


def _opaque(name: str, lineno: int) -> str:
    """A source token for a name whose binding this module cannot read through.

    ``plan = QuickstartPlan(...)`` binds ``plan`` to a value no identifier path
    describes. The binding is still a *source*, and it is the source of every
    read of ``plan`` until the next assignment to it — so the token carries the
    line of the binding, which makes two assignments to one name two sources
    and one assignment one source. That is precisely the object identity
    property (2) needs, and it is why the token is a path element rather than a
    separate model.

    Spelled ``name@lineno`` — ``plan@231`` — so a failure message names the
    assignment it means rather than only the identifier.
    """
    return f"{name}@{lineno}"


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

    ``path`` is where the bound value reads, or ``None`` when this module cannot
    read through it. **``None`` means present-but-unreadable, never absent** —
    that distinction is the whole of CR-01. A binding that is recorded as
    unreadable makes the downstream checks say "I cannot tell" (loudly, via
    :func:`_opaque`'s per-line token); a binding that is not recorded at all
    leaves the *previous* binding in force and makes them answer affirmatively
    about a value that is no longer there.

    ``until`` is set only for a **comprehension target**, whose binding does not
    escape the comprehension in Python 3. It is the last line of the
    comprehension expression, and it is what keeps ``[f(p) for p in ps]`` from
    rebinding ``p`` for the rest of the body. Every ``until``-carrying binding is
    constructed with ``path=None``, which is what keeps :func:`_resolve_at`
    terminating — see :func:`_binding_before`.
    """

    lineno: int
    path: tuple[str, ...] | None
    until: int | None = None


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

    What binds, and what it binds to:

    * ``a = expr`` / ``a = b = expr`` — the value's path, if it has one.
    * ``a: T = expr`` — the same. A bare ``a: T`` binds nothing and is skipped,
      which is what Python does.
    * ``(a := expr)`` — the same.
    * ``a, b = …`` / ``[a, b] = …`` / ``a, *rest = …`` — every name, unreadable:
      each is bound to an *element*, and which element is not a question an
      identifier path answers.
    * ``a += expr`` — unreadable. The new value derives from the old and from the
      right-hand side, and is neither; see the limits list in the module
      docstring for what that costs.
    * ``for a in …`` / ``async for a in …`` — unreadable, at the ``for`` line, so
      every read in the loop body resolves to it.
    * ``with … as a`` / ``async with … as a`` — unreadable, at the **statement's**
      line: ``ast.withitem`` carries no ``lineno``, and a binding recorded at
      line 0 sorts before every other and is therefore never in force, which is
      how this spelling stayed admitted under the review's own draft remedy.
    * ``except E as a`` — unreadable. Python unbinds the name at the end of the
      handler; an opaque token is closer to that than the pre-``try`` value.
    * ``import x`` / ``from m import y as a`` — unreadable. A module object has
      no identifier path, and ``import *`` binds names this cannot enumerate.
    * ``def a`` / ``async def a`` / ``class a`` — unreadable; both bind a name in
      the enclosing body.
    * ``case [a]`` / ``case *a,`` / ``case {**a}`` — unreadable, at the pattern's
      line.
    * a comprehension's ``for a in …`` — unreadable **and scoped** to the
      comprehension's own lines (``until``), because in Python 3 the target does
      not leak. Recording it unscoped would be red on the correct body
      ``plan = P(); bind(plan); [g(p) for plan in ps]; run(plan)``.

    Not bound here, and each named in the module docstring's limits: an
    attribute or subscript target (binds a member, not a local name);
    ``global``/``nonlocal`` (they redirect an assignment, they do not bind);
    ``del`` (unbinds — a subsequent read is a ``NameError``, so a body relying on
    it is broken before this module sees it).
    """
    line = getattr(node, "lineno", 0)
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                yield (target.id, _Binding(line, _binding_path(node.value)))
                continue
            for name in _bound_names(target):
                yield (name, _Binding(line, None))
    elif isinstance(node, ast.AnnAssign):
        if node.value is not None and isinstance(node.target, ast.Name):
            yield (node.target.id, _Binding(line, _binding_path(node.value)))
    elif isinstance(node, ast.NamedExpr):
        yield (node.target.id, _Binding(line, _binding_path(node.value)))
    elif isinstance(node, ast.AugAssign):
        for name in _bound_names(node.target):
            yield (name, _Binding(line, None))
    elif isinstance(node, ast.For | ast.AsyncFor):
        for name in _bound_names(node.target):
            yield (name, _Binding(line, None))
    elif isinstance(node, ast.With | ast.AsyncWith):
        for item in node.items:
            if item.optional_vars is None:
                continue
            for name in _bound_names(item.optional_vars):
                yield (name, _Binding(line, None))
    elif isinstance(node, ast.ExceptHandler):
        if node.name is not None:
            yield (node.name, _Binding(line, None))
    elif isinstance(node, ast.Import | ast.ImportFrom):
        for alias in node.names:
            if alias.name == "*":
                continue
            yield (alias.asname or alias.name.split(".")[0], _Binding(line, None))
    elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        yield (node.name, _Binding(line, None))
    elif isinstance(node, ast.MatchAs | ast.MatchStar):
        if node.name is not None:
            yield (node.name, _Binding(line, None))
    elif isinstance(node, ast.MatchMapping):
        if node.rest is not None:
            yield (node.rest, _Binding(line, None))
    elif isinstance(node, ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp):
        until = getattr(node, "end_lineno", None) or line
        for generator in node.generators:
            for name in _bound_names(generator.target):
                yield (name, _Binding(line, None, until))


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

    A list per name, sorted by line, answers the question the checks actually
    ask — *what was this name bound to at the point of use* — and
    :func:`_binding_before` is where that question is put.

    Traversal order is not relied on; the result is sorted explicitly, so this
    is independent of both ``_scope_nodes``'s stack order and dict iteration
    order. The sort key puts a comprehension's scoped binding **after** an
    unscoped one on the same line, so that a read inside the comprehension
    resolves to the comprehension's own target.
    """
    found: dict[str, list[_Binding]] = {}
    for node in _scope_nodes(scope):
        for name, binding in _binding_records(node):
            found.setdefault(name, []).append(binding)
    return {
        name: tuple(
            sorted(entries, key=lambda binding: (binding.lineno, binding.until is not None))
        )
        for name, entries in found.items()
    }


def _binding_before(
    name: str, line: int, bindings: dict[str, tuple[_Binding, ...]]
) -> _Binding | None:
    """The binding of ``name`` in force at ``line``: the last one above it.

    Strictly above, so ``x = x.y`` reads the *previous* ``x`` rather than
    itself. The cost of comparing lines rather than positions is that several
    statements separated by semicolons on one physical line resolve
    conservatively — none of them is "before" the others — which under-resolves
    rather than mis-resolves, and no file in the scanned trees is written that
    way.

    **A comprehension target is the one exception, and it is in force on its own
    line rather than strictly below it.** ``[run(plan=p) for p in ps]`` binds and
    reads ``p`` in one expression, so "strictly above" would resolve that read to
    whatever ``p`` was *before* the comprehension — the stale-binding answer
    CR-01 is about. A ``until``-carrying binding is therefore in force for
    ``lineno <= line <= until`` and for no other line, which is precisely the
    scope Python gives it.

    Every ``until``-carrying binding is built with ``path=None``
    (:func:`_binding_records` constructs them nowhere else), so the ``<=`` cannot
    hand :func:`_resolve_at` a binding it would follow to the same line and loop
    on. Termination is asserted rather than argued, over a comprehension that
    shadows the name it reads, in
    :func:`test_alias_resolution_terminates_on_a_cyclic_assignment_chain`.
    """
    latest: _Binding | None = None
    for binding in bindings.get(name, ()):
        if binding.until is None:
            if binding.lineno < line:
                latest = binding
        elif binding.lineno <= line <= binding.until:
            latest = binding
    return latest


def _resolve_at(
    path: tuple[str, ...] | None,
    line: int,
    bindings: dict[str, tuple[_Binding, ...]],
) -> tuple[str, ...] | None:
    """Where the value read by ``path`` at ``line`` comes from.

    ``a = execution.operators_invoked`` then ``b = a`` resolves a read of ``b``
    to ``("execution", "operators_invoked")``, so a chain of assignments is
    followed rather than only its first hop — the bypass cross-AI review raised
    against the sibling guard at the Phase 15 close. Each hop resolves the head
    **as of the line that bound it**, not as of the point of use, which is what
    makes the answer the one Python would give.

    **Termination is by construction.** Every hop replaces ``line`` with the
    line of a binding strictly above it, and :func:`_binding_before` only ever
    looks strictly above, so the line at which the walk is asking strictly
    decreases and the walk is bounded by the number of bindings in the body.
    The three-name rotation ``def f(b, c): a = b; b = c; c = a`` — legal,
    executable Python that hung the predecessor of this function with no output
    — terminates here in one hop per name and, better than terminating,
    resolves *correctly*: at the bottom of that body ``a`` and ``c`` both hold
    the parameter ``b``, which is what the code does.
    :func:`test_alias_resolution_terminates_on_a_cyclic_assignment_chain` holds
    both properties under a wall-clock bound.
    """
    if path is None:
        return None
    while True:
        head, *rest = path
        binding = _binding_before(head, line, bindings)
        if binding is None:
            return path
        if binding.path is None:
            return (_opaque(head, binding.lineno), *rest)
        path = (*binding.path, *rest)
        line = binding.lineno


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
                        _resolve_at(_path(argument), argument.lineno, bindings),
                    )
                )
        elif callee == LINEAGE_CONSTRUCTOR:
            argument = _keyword(node, LINEAGE_DECLARED_KEYWORD)
            if argument is not None:
                lineage_sides.append(
                    (
                        node.lineno,
                        _resolve_at(_path(argument), argument.lineno, bindings),
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

    Both halves, for the reason ``test_gate_independence.py:184-187`` gives: a
    check that always fires and a check that never fires each pass one half,
    and only the pair says the comparison is live.

    The probe bodies are **assembled** at runtime rather than written out, so
    this module's own source is not what a scan trips over — the discipline
    ``test_required_operators_guard.py:260-262`` and
    ``tests/examples/test_surface_audit.py`` both use. The check itself matches
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
    """
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


class _BinderCall(NamedTuple):
    """One ``refuse_operator_set_divergence`` call, with both sides resolved."""

    lineno: int
    declared: tuple[str, ...] | None
    handed: tuple[str, ...] | None
    plan_node: ast.expr | None


def _plan_sources(
    scope: ast.AST,
    bindings: dict[str, tuple[_Binding, ...]],
    plan_classes: frozenset[str] | None = None,
) -> dict[tuple[str, ...], tuple[str, ...] | None]:
    """Each plan construction, and where the ``required=`` it was built from reads.

    ``plan = QuickstartPlan(plan_id=…, required=requirements.required_operator_keys)``
    at line 231 binds the source token ``plan@231`` to
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
    construction in force at that line, so the two are two.
    """
    sources: dict[tuple[str, ...], tuple[str, ...] | None] = {}
    for node in _scope_nodes(scope):
        targets, value = _assignment(node)
        if value is None or not _is_plan_construction(value, plan_classes):
            continue
        assert isinstance(value, ast.Call)
        required = _keyword(value, PLAN_REQUIRED_KEYWORD)
        source = (
            None
            if required is None
            else _resolve_at(_path(required), required.lineno, bindings)
        )
        for target in targets:
            sources.setdefault((_opaque(target, getattr(node, "lineno", 0)),), source)
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
                lineno=node.lineno,
                declared=(
                    None
                    if declared_arg is None
                    else _resolve_at(
                        _path(declared_arg), declared_arg.lineno, bindings
                    )
                ),
                # `_binding_path`, not `_path`: `plan=` names an OBJECT, and the
                # question property (2) asks is which one. A call spelled here
                # is a fresh object no binder can have been handed, and the
                # inline branches below say so rather than resolving it.
                handed=(
                    None
                    if plan_arg is None
                    else _resolve_at(
                        _binding_path(plan_arg), plan_arg.lineno, bindings
                    )
                ),
                plan_node=plan_arg,
            )
        )
    return calls


class _Execution(NamedTuple):
    """One ``ProjectionEngine(...).execute(plan=…)`` and the plan it runs."""

    lineno: int
    plan: tuple[str, ...] | None
    plan_node: ast.expr | None


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
                lineno=node.lineno,
                plan=(
                    None
                    if argument is None
                    else _resolve_at(
                        _binding_path(argument), argument.lineno, bindings
                    )
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
        assert isinstance(call.plan_node, ast.Call)
        required = _keyword(call.plan_node, PLAN_REQUIRED_KEYWORD)
        return (
            None
            if required is None
            else _resolve_at(_path(required), required.lineno, bindings)
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
       hold unconditionally at ``binder.py:156-159``. The binder is green, it
       *cannot* fail, and ``ccf.projection-requirements`` has been routed
       around. This is CR-2's shape moved one seam upstream.
    2. **The plan bound is the plan run.** A binder handed one plan while the
       engine executes another checks a plan nothing assembles a product from.
    3. **The binder precedes the engine.** D-IMPL-86's correction places the
       call *between* plan construction and
       :meth:`~ccf.projection.engine.ProjectionEngine.execute`; a call after
       ``execute`` runs when a product has already been assembled from a set
       the deployment's own claim may contradict.

    **This does not close the authorship residual (R-3), and must not be read
    as doing so.** R-3 is the *authoring* boundary — an author copying one YAML
    document's keys into the other — and D-IMPL-86 establishes it as
    AST-undetectable *in principle*, because the compliant and the violating
    artifact are textually identical. What is checked here is **code**:
    ``required=declared.required_operator_keys`` is an identifier path this
    module already resolves, so it is detectable and now detected. The two
    remain separate findings and R-3 remains open.

    **A body with no binder call at all is reported here as well as by the
    coverage assertion, and that is deliberate** (IN-03).
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
    """
    bindings = _bindings(scope)
    sources = _plan_sources(scope, bindings, plan_classes)
    calls = _binder_calls(scope, bindings)
    executions = _executions(scope, bindings)
    where = path.relative_to(REPO_ROOT)
    problems: list[str] = []

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

    # (3) ordering, for the case (2) cannot read
    first_execution = min(
        (execution.lineno for execution in executions), default=None
    )
    if first_execution is not None and not any(
        call.lineno < first_execution for call in calls
    ):
        problems.append(
            f"{where}:{first_execution}: a projection is executed here with no"
            f" `{BINDER_CALL}` call before it. The binder belongs BETWEEN plan"
            " construction and `ProjectionEngine.execute` (D-IMPL-86"
            " correction, 2026-08-05); after the engine has run, a product has"
            " already been assembled from a set the deployment's own claim may"
            " contradict."
        )

    # (2) the plan bound is the plan run
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
                f"{ENGINE_PLAN_KEYWORD}=` argument, so no `{BINDER_CALL}` call"
                " can have been handed that object. Hoist the plan into a"
                " local and call the binder on the line between (D-IMPL-86"
                " correction, 2026-08-05)."
            )
            continue
        if execution.plan is None:
            continue  # an unreadable plan expression — a stated limit, not a pass
        if any(
            call.handed == execution.plan and call.lineno < execution.lineno
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

    What is still not asserted, stated exactly: **reachability**. A binder call
    inside a never-taken ``if``, an ``except`` handler, or a
    ``# pragma: no cover`` branch is named, is ordered before the engine, and
    never runs. Ordering is checkable from line numbers and is now checked;
    reachability is genuinely out of an AST walk's reach and is left named
    rather than implied away.
    """
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


# --- tripwire (2), the argument half: the binder is doing something -----------


def _resolved_binder_sites() -> list[str]:
    """Binder calls whose handed plan's ``required=`` this module can read.

    The input :func:`_binder_collapses`'s first check consumes. A binder call
    whose plan is out of reach is scanned and says nothing, so counting the
    *readable* ones is what distinguishes a live check from a quiet one.
    """
    readable: list[str] = []
    for path, scope in _projecting_scopes():
        bindings = _bindings(scope)
        sources = _plan_sources(scope, bindings)
        for call in _binder_calls(scope, bindings):
            if _handed_plan_source(call, sources, bindings) is None:
                continue
            readable.append(f"{path.relative_to(REPO_ROOT)}:{call.lineno}")
    return readable


def test_the_binder_argument_scan_is_not_vacuous() -> None:
    """The argument checks are handed something to compare — a count over the tree.

    The two coverage floors say bodies were *found*. This one says the checks
    that read the binder's arguments were handed something to compare. A check
    that matched every body and could resolve none of their plans would report
    zero problems forever — CR-03's failure mode restated one layer in.

    **This assertion is a total, and a total is not a per-site property** — the
    distinction WR-F3 drew, and the reason its companion below exists. The two
    counts coincide today at eleven bodies and eleven readable sites, so any body
    that gains a readable site while another loses one leaves this green. Keep
    both: this one catches a site disappearing from the tree, and
    :func:`test_every_bound_body_has_a_readable_plan_source` catches a body
    whose own plan the checks cannot read. Neither statement implies the other.
    """
    found = _resolved_binder_sites()
    assert len(found) >= MINIMUM_RESOLVED_BINDER_SITES, (
        f"{len(found)} binder call sites with a readable plan source,"
        f" {MINIMUM_RESOLVED_BINDER_SITES} expected."
        f" {FLOOR_REMOVAL_INSTRUCTION} Found: {found}"
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
    existing eleven still contribute eleven, and ``11 >= 11`` holds. Both CR-F1
    and WR-F1 exploit exactly that arithmetic.

    **Per call, not per body (WR-02).** The first version of this assertion was
    ``any(...)``, which composes the same arithmetic one level down: a body with
    one compliant readable site absorbs any number of unreadable ones beside it,
    so a plan class this module does not recognise routes around property (1)
    while this assertion stays green. Measured over the tree, ``all()`` costs
    nothing today — eleven projecting bodies, eleven binder calls, **zero**
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
    required`` holds unconditionally at ``binder.py:156-159``.

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
        # the compliant shape at all nine executing sites: the plan reads the
        # projection's own artifact, the binder reads the product class's claim
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
        assert all(binding.lineno > 0 for binding in bindings["a"]), (
            f"{label} recorded a binding at line 0, which sorts before every"
            " other and is therefore never in force — the trap `ast.withitem`"
            " sets, since it carries no `lineno` of its own"
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

    **The evidence base is n = 1, stated rather than left to be discovered**
    (IN-02). Measured 2026-08-06: twelve calls under ``examples/`` pass
    ``required=``, eleven of them are plan constructions, and the twelfth is
    ``examples/03-harness-portability/run.py:693``'s ``add_argument``. So making
    that one CLI flag optional, or retiring example 03, turns a
    ``tests/products/`` Gate-2 test red for a reason with nothing to do with
    Gate 2. That is the deliberate trade above — a loud, self-explaining failure
    is preferable to the rule quietly ceasing to be demonstrated — but a reader
    is entitled to know the count is one and not many.
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
    resolves each hop as of the line that bound it, so the walk strictly ascends
    the body and terminates by construction, and the answer it terminates on is
    the one Python gives: at the bottom of the rotation ``a`` and ``c`` both hold
    the parameter ``b``, and ``b`` holds the parameter ``c``. The assertion below
    is therefore *stronger* than its predecessor's inequality, not weaker: it
    pins the semantics rather than the fallback.
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
            name: _resolve_at((name,), 5, bindings) for name in ("a", "b", "c")
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
        assert _resolve_at(("a",), 5, grown) == ("b", "k")

    # A two-name cycle and a self-assignment were already survivable; they stay
    # so, and are asserted rather than assumed.
    for source, name in (
        ("def f(b):\n    a = b\n    b = a\n", "a"),
        ("def f(a):\n    a = a.k\n", "a"),
    ):
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        with _within(5.0):
            assert _resolve_at((name,), 99, _bindings(function)) is not None

    # A comprehension binding is in force ON its own line rather than strictly
    # below it (:func:`_binding_before`), which is the one place the walk could
    # ask about a line it is already at. It terminates because every such
    # binding is unreadable and :func:`_resolve_at` stops at an unreadable one —
    # asserted here rather than argued, over a comprehension that shadows the
    # name it reads and one that shadows a name bound above it.
    shadowing = ast.parse(
        "def f(xs, y):\n"
        "    a = y.k\n"
        "    b = [a for a in xs]\n"
        "    return a\n"
    ).body[0]
    assert isinstance(shadowing, ast.FunctionDef)
    with _within(5.0):
        shadow_bindings = _bindings(shadowing)
        inside = _resolve_at(("a",), 3, shadow_bindings)
        after = _resolve_at(("a",), 4, shadow_bindings)
    # inside the comprehension the name is the comprehension's own target, which
    # this module cannot read through; after it, the binding above is back in
    # force, because a comprehension target does not leak in Python 3
    assert inside == (_opaque("a", 3),)
    assert after == ("y", "k")


def test_the_wall_clock_bound_is_itself_live() -> None:
    """``_within`` fires — otherwise the termination test proves nothing.

    A bound that never triggers passes every body, including one that hangs.
    """
    with pytest.raises(_TookTooLong):
        with _within(0.05):
            while True:  # noqa: WPS457 - deliberately non-terminating
                pass
