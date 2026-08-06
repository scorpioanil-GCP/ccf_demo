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

Every lexical body under ``examples/`` that constructs a projection plan, or
runs one through ``ProjectionEngine(...).execute(...)``, must **name**
:func:`ccf.deployment.refuse_operator_set_divergence`.

``refuse_operator_set_divergence`` returns ``None`` by contract — deliberately,
so it can never grow into a helper that supplies one of Gate 2's arguments. The
consequence is that **nothing observable at runtime proves the call happened**:
no product field, no pin, no audit event. A deployment that omits it produces
output byte-identical to one that made it. An AST check is therefore the only
mechanism available, and this module claims exactly that and no more.

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
import pathlib
from collections.abc import Iterator

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
    return value, a subscript, a dynamic attribute access — yields ``None``,
    and the docstring names each of those as a limit rather than pretending
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
        if isinstance(node.func, ast.Attribute):
            # A method call reads off its receiver: `execution.resolved()`.
            return _path(node.func.value)
        if isinstance(node.func, ast.Name) and node.args:
            if node.func.id in TRANSPARENT_CONVERSIONS:
                return _path(node.args[0])
            if node.func.id == TRANSPARENT_CAST and len(node.args) > 1:
                # `cast(T, value)` is a no-op at runtime; the value is arg 2.
                return _path(node.args[1])
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

    while True:
        grew = False
        for name, path in list(bindings.items()):
            head, *rest = path
            if head == name or head not in bindings:
                continue
            resolved = (*bindings[head], *rest)
            if resolved != path and name not in resolved:
                bindings[name] = resolved
                grew = True
        if not grew:
            return bindings


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
    assert len(found) >= MINIMUM_GATE_CALL_SITES, [
        f"{path.relative_to(REPO_ROOT)}:{_scope_line(scope)}"
        for path, scope in found
    ]


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
    for node in _scope_nodes(scope):
        if isinstance(node, ast.Call) and _callee(node) == BINDER_CALL:
            return True
    return False


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
    """The floor is counted from the tree, and asserted rather than assumed."""
    found = _projecting_scopes()
    assert len(found) >= MINIMUM_PROJECTING_BODIES, [
        f"{path.relative_to(REPO_ROOT)}:{_scope_line(scope)}"
        f" {_scope_label(scope)}"
        for path, scope in found
    ]


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
    """D-IMPL-86 element (3), as corrected 2026-08-05.

    The binder returns ``None``, so no runtime evidence of the call exists and
    an AST check is the only mechanism there is. This asserts the call is
    *named*; it does not and cannot assert it was reached.
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
