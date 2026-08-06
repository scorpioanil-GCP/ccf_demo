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

Local aliases are followed to a fixed point over assignment, annotated
assignment and the walrus, so ``resolved = execution.operators_invoked`` used on
both sides is caught rather than evaded by one statement. Set conversions
(``frozenset``, ``tuple``, ``sorted``, and ``typing.cast``) are transparent, so
wrapping one side does not hide it.

What tripwire (1) cannot catch — the structural limit, not a caution
---------------------------------------------------------------------

* A value arriving through **a helper's return value**. ``derive(execution)``
  roots at the helper, and this module deliberately stops there rather than
  guessing what the helper returns.
* A value arriving through **a method's return value**. ``execution.resolved()``
  stops at the call for the same reason, and it is worth stating why the
  tempting shortcut is wrong rather than merely unimplemented: reading a method
  call off its receiver makes *any* method call on an object share a source
  with *any* attribute read of it, so ``self.declared_claim()`` paired with
  ``self._resolved`` is reported as a collapse and the check is **red on
  correct code**. That is the very ``self`` collapse the paths-not-roots rule
  above exists to prevent, re-entering through the call node. A method is a
  member of its receiver exactly as an attribute is, and which member it
  returns is not something an AST walk knows.
* A value arriving through **a container** — ``results["ops"]`` — or through
  **dynamic attribute access** — ``getattr(execution, "operators_" + "invoked")``.
  Neither has an identifier path an AST walk can read.
* A value carried across a **body boundary** by an attribute set in one method
  and read in another.
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
* **A plan crossing a body boundary.** A plan constructed and bound in one
  method and executed in another is two bodies, and one body means one body.
* **A plan class not named ``*Plan`` that is never executed in its own body.**
  Plan *construction* is recognised by the class-name suffix, which is a
  convention. Plan *execution* is not: ``ProjectionEngine.execute`` declares
  ``plan`` keyword-only, so any body that runs a projection through the SDK's
  engine passes ``plan=`` whatever its plan class is called and is detected
  regardless. The surviving hole is therefore narrow — a non-``Plan``-suffixed
  class constructed and *returned* rather than executed, the ``resolve_plan``
  shape — and it is stated here rather than papered over with a second
  convention.

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

#: A projection plan construction, by the two properties every implementation
#: of :class:`ccf.projection.plan.ProjectionPlan` in the suite shares: a class
#: name ending in ``Plan``, and a ``required`` keyword carrying the operator
#: set it declares.
PLAN_CLASS_SUFFIX = "Plan"
PLAN_REQUIRED_KEYWORD = "required"

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


def _path(node: ast.expr) -> tuple[str, ...] | None:
    """The dotted identifier path an expression reads, if it has one.

    ``execution.operators_invoked`` yields ``("execution", "operators_invoked")``;
    ``frozenset(declared.required_operator_keys)`` yields
    ``("declared", "required_operator_keys")``, because a set conversion is
    transparent to its argument; ``self._declared`` yields
    ``("self", "_declared")``, which is what keeps two attributes of one object
    distinguishable. Anything whose source an AST walk cannot read — a helper's
    return value, **a method's return value**, a subscript, a dynamic attribute
    access — yields ``None``, and the docstring names each of those as a limit
    rather than pretending otherwise.
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
        if isinstance(node.func, ast.Name) and node.args:
            if node.func.id in TRANSPARENT_CONVERSIONS:
                return _path(node.args[0])
            if node.func.id == TRANSPARENT_CAST and len(node.args) > 1:
                # `cast(T, value)` is a no-op at runtime; the value is arg 2.
                return _path(node.args[1])
        # A METHOD's return value is out of reach, exactly as a helper's is.
        # Reading `obj.method()` off its receiver as `("obj",)` looks like it
        # sees through the call and does not: it makes *any* method call on an
        # object share a source with *any* attribute read of it, so
        # `self.declared_claim()` paired with `self._resolved` reports a
        # collapse that is not there. That is the `self` collapse the design
        # rule three paragraphs up exists to avoid, reintroduced through the
        # call node. A method is a member of its receiver in exactly the way an
        # attribute is; this module cannot know whether it returns a sibling
        # member or something unrelated, and it stops rather than guessing.
        return None
    return None


def _assignment(node: ast.AST) -> tuple[list[str], ast.expr | None]:
    """Local names bound by one statement, and the expression bound to them."""
    if isinstance(node, ast.Assign):
        return ([t.id for t in node.targets if isinstance(t, ast.Name)], node.value)
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return ([node.target.id], node.value)
    if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
        return ([node.target.id], node.value)
    return ([], None)


def _aliases(scope: ast.AST) -> dict[str, tuple[str, ...]]:
    """Local aliases in one body, resolved to a fixed point.

    ``a = execution.operators_invoked`` then ``b = a`` binds both ``a`` and
    ``b`` to ``("execution", "operators_invoked")``, so a chain of assignments
    is followed rather than only its first hop. Cross-AI review at the Phase 15
    close raised exactly this bypass against the sibling guard; it is closed the
    same way here, and
    :func:`test_the_tripwire_detects_the_shape_it_exists_to_refuse` exercises it.

    **Termination is by construction, not by convergence.** Each name is
    resolved independently by walking its own chain while carrying the set of
    heads already substituted; a head that reappears ends that walk. Every
    iteration adds one element to a set bounded by ``bindings``, so the walk is
    bounded by ``len(bindings) + 1`` steps for every name.

    The predecessor of this function grew a shared binding map until nothing
    changed, and **did not terminate on a three-name rotation** —
    ``def f(b, c): a = b; b = c; c = a`` — where the substitution oscillates
    forever and ``grew`` is never ``False``. That rotation is legal, executable
    Python, so *refusing* it would be red on correct code; it is resolved
    conservatively instead, each name to itself, which is distinct per name and
    so cannot manufacture a shared source. Because this scan runs over every
    ``.py`` file under ``src/``, ``runtime/`` and ``examples/``, the old shape
    meant one contributor's rotation chain hung ``pytest`` with no output.
    :func:`test_alias_resolution_terminates_on_a_cyclic_assignment_chain` holds
    the property under a wall-clock bound, so a regression fails rather than
    hangs.

    Resolving from the raw first-assignment map rather than mutating it in
    place also makes the result independent of dict iteration order.
    """
    bindings: dict[str, tuple[str, ...]] = {}
    for node in _scope_nodes(scope):
        targets, value = _assignment(node)
        if value is None:
            continue
        path = _path(value)
        if path is None:
            continue
        for target in targets:
            bindings.setdefault(target, path)

    resolved: dict[str, tuple[str, ...]] = {}
    for name, path in bindings.items():
        substituted = {name}
        head = path[0]
        while head in bindings and head not in substituted:
            substituted.add(head)
            path = (*bindings[head], *path[1:])
            head = path[0]
        resolved[name] = path
    return resolved


def _resolve(
    path: tuple[str, ...] | None, aliases: dict[str, tuple[str, ...]]
) -> tuple[str, ...] | None:
    if path is None:
        return None
    head, *rest = path
    if head not in aliases:
        return path
    substituted = aliases[head]
    if head in substituted:  # pragma: no cover - defensive against `x = x.y`
        return path
    return (*substituted, *rest)


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
    aliases = _aliases(scope)
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
                    (node.lineno, _resolve(_path(argument), aliases))
                )
        elif callee == LINEAGE_CONSTRUCTOR:
            argument = _keyword(node, LINEAGE_DECLARED_KEYWORD)
            if argument is not None:
                lineage_sides.append(
                    (node.lineno, _resolve(_path(argument), aliases))
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
                f" read `{'.'.join(declared)}`."
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


def _is_plan_construction(node: ast.AST) -> bool:
    """A projection plan being built: ``<Something>Plan(..., required=...)``."""
    if not isinstance(node, ast.Call):
        return False
    callee = _callee(node)
    if callee is None or not callee.endswith(PLAN_CLASS_SUFFIX):
        return False
    return any(
        keyword.arg == PLAN_REQUIRED_KEYWORD for keyword in node.keywords
    )


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
    scope: ast.AST, aliases: dict[str, tuple[str, ...]]
) -> dict[tuple[str, ...], tuple[str, ...] | None]:
    """Each local bound to a plan construction, and where its ``required=`` reads.

    ``plan = QuickstartPlan(plan_id=…, required=requirements.required_operator_keys)``
    binds ``("plan",)`` to ``("requirements", "required_operator_keys")``. That
    mapping is the whole basis of the tautology check: the binder is handed
    ``plan``, and this says which of the two authored documents ``plan`` was
    built from.
    """
    sources: dict[tuple[str, ...], tuple[str, ...] | None] = {}
    for node in _scope_nodes(scope):
        targets, value = _assignment(node)
        if value is None or not _is_plan_construction(value):
            continue
        assert isinstance(value, ast.Call)
        required = _keyword(value, PLAN_REQUIRED_KEYWORD)
        source = None if required is None else _resolve(_path(required), aliases)
        for target in targets:
            sources.setdefault((target,), source)
    return sources


def _binder_calls(
    scope: ast.AST, aliases: dict[str, tuple[str, ...]]
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
                    else _resolve(_path(declared_arg), aliases)
                ),
                handed=(
                    None if plan_arg is None else _resolve(_path(plan_arg), aliases)
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
    scope: ast.AST, aliases: dict[str, tuple[str, ...]]
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
                    None if argument is None else _resolve(_path(argument), aliases)
                ),
                plan_node=argument,
            )
        )
    return found


def _handed_plan_source(
    call: _BinderCall,
    sources: dict[tuple[str, ...], tuple[str, ...] | None],
    aliases: dict[str, tuple[str, ...]],
) -> tuple[str, ...] | None:
    """Where the ``required=`` of the plan handed to ``call`` reads, if readable."""
    if call.plan_node is not None and _is_plan_construction(call.plan_node):
        # `binder(declared=…, plan=FooPlan(required=…))` — inline, read directly.
        assert isinstance(call.plan_node, ast.Call)
        required = _keyword(call.plan_node, PLAN_REQUIRED_KEYWORD)
        return None if required is None else _resolve(_path(required), aliases)
    if call.handed is None:
        return None
    return sources.get(call.handed)


def _binder_collapses(scope: ast.AST, path: pathlib.Path) -> list[str]:
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
    """
    aliases = _aliases(scope)
    sources = _plan_sources(scope, aliases)
    calls = _binder_calls(scope, aliases)
    executions = _executions(scope, aliases)
    where = path.relative_to(REPO_ROOT)
    problems: list[str] = []

    # (1) the binder's two sides must be two documents
    for call in calls:
        required = _handed_plan_source(call, sources, aliases)
        if not _shares_a_source(call.declared, required):
            continue
        assert call.declared is not None and required is not None
        problems.append(
            f"{where}:{call.lineno}: the plan handed to `{BINDER_CALL}` reads"
            f" its `{PLAN_REQUIRED_KEYWORD}=` from `{'.'.join(required)}`, which"
            f" is the same source as `{BINDER_DECLARED_KEYWORD}="
            f"{'.'.join(call.declared)}`. The binder then compares a value"
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
            execution.plan_node
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
            f" `{'.'.join(execution.plan)}`, which no `{BINDER_CALL}` call in"
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
        aliases = _aliases(scope)
        sources = _plan_sources(scope, aliases)
        for call in _binder_calls(scope, aliases):
            if _handed_plan_source(call, sources, aliases) is None:
                continue
            readable.append(f"{path.relative_to(REPO_ROOT)}:{call.lineno}")
    return readable


def test_the_binder_argument_scan_is_not_vacuous() -> None:
    """The argument checks are handed something to compare, at every site.

    The two coverage floors say bodies were *found*. This one says the checks
    that read the binder's arguments can actually see, at each of those sites,
    which document the handed plan was built from. A check that matched every
    body and could resolve none of their plans would report zero problems
    forever — CR-03's failure mode restated one layer in.
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
        # a workflow execution is not a projection and carries no binder
        "def drive(engine, workflow, execution_id):\n"
        "    return engine.execute(workflow, execution_id=execution_id)\n",
    )
    for source in benign:
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert not _binder_collapses(function, REPO_ROOT / "probe.py"), source


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
    """``_aliases`` returns on a rotation instead of spinning forever.

    A three-name rotation is legal, executable Python — ``a`` takes ``b``'s
    value, ``b`` takes ``c``'s, ``c`` takes the old ``a`` — so the answer to it
    has to be a *result*, not a refusal; refusing would be red on correct code,
    which is the defect this module was separately found to have elsewhere.

    The predecessor of :func:`_aliases` grew a shared binding map to a fixed
    point and never reached one here: ``a`` settled at ``(c,)``, ``c`` at
    ``(a,)``, and ``b`` alternated between the two forever. Since the scan runs
    over every ``.py`` file under ``src/``, ``runtime/`` and ``examples/``, one
    contributor writing that shape hung ``pytest`` with no output and no
    timeout to break it. The bound below is what makes a regression *fail*
    rather than hang.
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
        resolved = _aliases(rotation)

    # Each rotating name resolves to itself: terminating, and — the part that
    # matters for tripwire (1) — still three distinct sources, so a cycle
    # cannot manufacture a shared one.
    assert resolved["a"] != resolved["b"] != resolved["c"]

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
        _aliases(growing)

    # A two-name cycle and a self-assignment were already survivable; they stay
    # so, and are asserted rather than assumed.
    for source in (
        "def f(b):\n    a = b\n    b = a\n",
        "def f(a):\n    a = a.k\n",
    ):
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        with _within(5.0):
            _aliases(function)


def test_the_wall_clock_bound_is_itself_live() -> None:
    """``_within`` fires — otherwise the termination test proves nothing.

    A bound that never triggers passes every body, including one that hangs.
    """
    with pytest.raises(_TookTooLong):
        with _within(0.05):
            while True:  # noqa: WPS457 - deliberately non-terminating
                pass
