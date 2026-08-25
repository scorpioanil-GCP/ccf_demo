"""G-B — no projection derives `required_operators()` from the registry's keys.

Plan 15-13 changed `archive/examples/00-quickstart`'s `QuickstartPlan.required_operators()`
to declare its keys from the `ccf.product-class` artifact rather than return
`operators.keys()`, and 15-14 through 15-20 carried the same change through the
rest of the suite. **That closes the instances. It does not close the pattern.**

Why the shortcut is a governance defect and not a style one
------------------------------------------------------------

Stated precisely, because the imprecise version is easy to repeat and wrong.
**Gate 2 itself** — lineage strict equality, whitepaper §7.6, INV-CH7-47 —
compares `candidate.lineage.operators_invoked` against `engine_resolved` inside
`ccf.products.gates.run_gates`. `required_operators()` is **upstream of** that
comparison, not one of its two arguments: it is the plan's *declaration*, and
the engine plans from it and then observes what it ran.

The independence that matters here is therefore one level up. If a projection
declares whatever the operator registry happens to hold, the plan is no longer
an independent statement of what the product needs — it is a restatement of the
engine's own configuration, and everything downstream that treats it as a claim
(the empty-operator guard, and every test comparing declared keys against
resolved ones) is comparing a value with itself. It stays green. The invariant
is gone, and nothing fails to say so.

That is the same collapse `tests/products/test_gate_independence.py` exists to
prevent, one level up: that module stops a *helper* deriving both of Gate 2's
arguments from one input; this module stops a *projection* deriving its
declaration from the engine.

The phase found this shape eight times, twice as an outright correctness defect
(`15-17-SUMMARY.md`, where the tautology sat in the original decision **and** in
the forensic replay meant to prove it; `15-18-SUMMARY.md`, where an A2A
entitlement check compared two reads of the producer's own file). Neither was
visible until typed artifacts gave the declared side an authored source.
Instance-by-instance repair is therefore not enough — the next projection
someone writes has to be refused, not reviewed.

Why AST identifiers and not source text
----------------------------------------

Matched on `ast.Attribute` / `ast.Name` nodes, exactly as 15-02's guard is, and
for the same two reasons: a source-text grep is fooled by a comment or a
docstring that merely *mentions* `operators.keys()` — including this module's
own — and it cannot see through the spellings the phase actually found
(`self._registry().keys()`, a local alias, a walrus).

**What the AST approach does and does not buy.** It follows *receiver aliasing*
to a fixed point, so `ops = self._registry()` and a chain of such assignments
are caught. It is **not** dataflow analysis: a receiver that arrives through a
helper function's return value, through a container, or through a name this
module does not recognise as the registry is out of reach. The refused-receiver
set is a convention list, and a projection that named its registry something
else entirely would pass. The claim this module supports is "the shortcut, in
every spelling the phase found, and in the obvious evasions of them" — not
"impossible to write".

What is deliberately not flagged
---------------------------------

Reading `.keys()` off something that is not the operator registry — a parameters
mapping, a declaration dict — is legitimate and common. The guard therefore
names the receivers it refuses (`operators`, `registry`, `_registry`, plus the
enclosing function's own parameter names) rather than refusing every `.keys()`
call, so it stays a check on the collapse rather than a ban on a method.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The trees a projection can live in. `tests/` is deliberately excluded: a
#: test may legitimately build a deliberately-tautological plan to prove a
#: guard fires, and this module is one of the places that happens.
#:
#: `archive` joined in plan `23-03`, ahead of Phase 23's move of ten condemned
#: example trees into `archive/examples/` (`D-03`). Nine of the fourteen
#: `required_operators` implementations this scan finds live in those ten
#: trees, so without the member the scan would find five after the move and
#: :data:`MINIMUM_IMPLEMENTATIONS` would go red in a way that reads like a
#: legitimate removal. **Widening the root is the honest fix and lowering the
#: floor is not**: the same witnesses are found at the new path, so the count
#: is preserved exactly, whereas a lowered floor buys a green build by
#: shedding the coverage the floor exists to hold.
#:
#: The member is the top-level `archive`, matching this tuple's existing shape
#: (tree names joined to `REPO_ROOT`, not path prefixes) — the same inheriting
#: spelling `tools/lints/__main__.py::LINTED_TREES` took, and deliberately
#: NOT the narrow spelling the default-deny publication allowlist took in plan
#: `23-02`. Guarded by
#: :func:`test_the_scan_root_membership_is_exactly_the_expected_set`, because
#: the floor below cannot see one root being swapped for another.
SCANNED_TREES: tuple[str, ...] = ("src", "runtime", "examples", "archive")

#: The method whose return value is the declared side of Gate 2.
TARGET_METHOD = "required_operators"

#: Receiver names that mean "the operator registry" by convention across the
#: SDK and the suite. Matched as identifiers, never as text.
REGISTRY_RECEIVERS: frozenset[str] = frozenset(
    {"operators", "operator_registry", "registry", "_registry", "_operators"}
)

#: The suite carries one projection per example plus the SDK's own Protocol and
#: acquisition plan. A scan that silently matched zero functions is the
#: quietest way this guard stops being one, so the floor is asserted.
MINIMUM_IMPLEMENTATIONS = 9


def _python_sources() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for tree in SCANNED_TREES:
        found.extend(sorted((REPO_ROOT / tree).rglob("*.py")))
    return found


def _receiver_name(node: ast.expr) -> str | None:
    """The identifier a `.keys` access is reading off, if it has one.

    `operators.keys` yields ``operators``; `self._registry().keys` yields
    ``_registry``; `(ops := self._registry()).keys` yields ``_registry``,
    because the walrus is a way of spelling the same read. Anything with no
    identifier at its root yields ``None``.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _receiver_name(node.func)
    if isinstance(node, ast.NamedExpr):
        return _receiver_name(node.value)
    if isinstance(node, ast.Await):
        return _receiver_name(node.value)
    return None


def _assignment_targets(node: ast.stmt) -> tuple[list[str], ast.expr | None]:
    """Local names bound by one statement, and the expression bound to them."""
    if isinstance(node, ast.Assign):
        return (
            [t.id for t in node.targets if isinstance(t, ast.Name)],
            node.value,
        )
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return ([node.target.id], node.value)
    if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
        return ([node.target.id], node.value)
    return ([], None)


def _refused_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Receiver names that mean "the operator registry" inside this body.

    The conventional names, plus the function's own parameters, plus **any
    local alias of either** — ``ops = operators`` and
    ``ops = self._registry()`` both bind ``ops`` to the registry, and a guard
    that missed them would be defeated by one assignment. Cross-AI review at
    the Phase 15 close raised exactly that bypass; it is closed here rather
    than argued about, and `test_the_guard_detects_the_shortcut_it_exists_to_refuse`
    exercises both spellings.

    Iterated to a fixed point, so a chain of aliases is followed rather than
    only the first hop.
    """
    refused = set(REGISTRY_RECEIVERS)
    refused |= {
        argument.arg
        for argument in (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
        if argument.arg != "self"
    }
    while True:
        grew = False
        for node in ast.walk(function):
            if not isinstance(node, ast.stmt | ast.NamedExpr):
                continue
            targets, value = _assignment_targets(node)
            if value is None:
                continue
            source = _receiver_name(value)
            if source is None or source not in refused:
                continue
            for target in targets:
                if target not in refused:
                    refused.add(target)
                    grew = True
        if not grew:
            return refused


def _violations(
    function: ast.FunctionDef | ast.AsyncFunctionDef, path: pathlib.Path
) -> list[str]:
    """Every `<registry>.keys` read inside one `required_operators` body."""
    refused = _refused_names(function)

    problems: list[str] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Attribute) or node.attr != "keys":
            continue
        receiver = _receiver_name(node.value)
        if receiver is None or receiver not in refused:
            continue
        problems.append(
            f"{path.relative_to(REPO_ROOT)}:{node.lineno}:"
            f" {TARGET_METHOD}() reads `{receiver}.keys()`."
            " The projection's required operator set must be AUTHORED, not"
            " read back out of the engine's own registry: a plan that declares"
            " whatever happens to be registered makes everything downstream"
            " that treats the declaration as a claim — the empty-operator"
            " guard, and every check comparing declared keys against resolved"
            " ones — compare a value against itself. It passes, and the"
            " invariant (whitepaper §7.6, INV-CH7-47) is gone with nothing"
            " failing to say so."
            " Declare the keys from the projection's own"
            " `ccf.projection-requirements` artifact"
            " (`required_operator_keys`) instead. Since D-IMPL-86 (design E2)"
            " that is the plan's source; the `ccf.product-class` artifact is"
            " the product's separately authored CLAIM, and"
            " `ccf.deployment.binder.refuse_operator_set_divergence` refuses"
            " when the two disagree."
        )
    return problems


def _implementations() -> list[tuple[pathlib.Path, ast.FunctionDef | ast.AsyncFunctionDef]]:
    found: list[tuple[pathlib.Path, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for path in _python_sources():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - a broken file fails elsewhere
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                and node.name == TARGET_METHOD
            ):
                found.append((path, node))
    return found


def test_the_scan_is_not_vacuous() -> None:
    """A guard that matched zero functions would pass forever."""
    found = _implementations()
    assert len(found) >= MINIMUM_IMPLEMENTATIONS, [
        str(path.relative_to(REPO_ROOT)) for path, _ in found
    ]


def test_the_scan_root_membership_is_exactly_the_expected_set() -> None:
    """The floor above cannot see a root SWAP. This is the half that can.

    ``23-RESEARCH.md`` finding **S-16**, stated at its sharpest here: setting
    ``SCANNED_TREES = ("archive",)`` after Phase 23's move keeps
    :data:`MINIMUM_IMPLEMENTATIONS` green on the very same witnesses — they
    were merely renamed — while every projection under the SURVIVING
    ``examples/`` trees silently stops being scanned. Both the count and the
    exit code stay identical. A floor asserts a total, not a source.

    So the source is asserted, and by set equality rather than by ``in``
    checks: an ``in`` check passes over a tuple that has grown, and a tree
    joining this scan quietly is the other direction of the same problem.

    ``tests/`` stays excluded for the reason the constant's own comment
    gives — a test may build a deliberately-tautological plan to prove a guard
    fires — and ``archive`` was added in plan ``23-03``, before the move, so
    that the widening could be proven a no-op while the archive did not yet
    exist. The floor was NOT touched: widening the root preserves the count
    exactly, because the same witnesses are found at the new path. Lowering
    the floor is the fix that loses the coverage.
    """
    assert set(SCANNED_TREES) == {"src", "runtime", "examples", "archive"}, (
        "this guard's scan roots changed. A root REMOVED stops a tree being"
        " scanned with the floor still green; a root ADDED widens the guard"
        " without review. Neither is visible in a count."
    )
    assert "examples" in SCANNED_TREES, (
        "the live examples tree left the scan. After Phase 23 it still holds"
        " the surviving example trees, and they are the ones a swap loses."
    )
    assert "archive" in SCANNED_TREES, (
        "the archive left the scan. The ten condemned example trees keep their"
        " projections after the move; a scan that stops at the archive"
        " boundary reports a smaller tree, not a cleaner one."
    )


@pytest.mark.parametrize(
    ("path", "function"),
    _implementations(),
    ids=lambda value: (
        str(value.relative_to(REPO_ROOT)) if isinstance(value, pathlib.Path) else ""
    ),
)
def test_no_required_operators_reads_the_registrys_own_keys(
    path: pathlib.Path, function: ast.FunctionDef | ast.AsyncFunctionDef
) -> None:
    """G-B at the pattern: a tripwire over the receivers this module names."""
    problems = _violations(function, path)
    assert not problems, "\n".join(problems)


def test_the_guard_detects_the_shortcut_it_exists_to_refuse() -> None:
    """The guard is verified to refuse, not merely observed to pass.

    A structural check nobody has watched fail is a check that might be
    matching nothing at all. Both spellings the phase actually found are
    exercised: the bare parameter (`15-13`, `15-20`'s `serve.py`) and the
    method call (`15-17`, `15-20`'s replay environment).
    """
    # The probe bodies are *assembled* rather than written out, so this
    # module's own source cannot be what a text scan trips over — the same
    # discipline `tests/examples/test_surface_audit.py` uses for the figures
    # it forbids. The check itself matches `ast.Attribute`, never text.
    reads = ".".join(("", "keys()"))
    for source in (
        # the bare parameter — 15-13, and 15-20's `serve.py`
        f"def {TARGET_METHOD}(self, operators):\n"
        f"    return frozenset(operators{reads})\n",
        # the method call — 15-17, and 15-20's replay environment
        f"def {TARGET_METHOD}(self):\n"
        f"    return tuple(self._registry(){reads})\n",
        # one alias hop off a parameter
        f"def {TARGET_METHOD}(self, operators):\n"
        "    ops = operators\n"
        f"    return frozenset(ops{reads})\n",
        # one alias hop off a call
        f"def {TARGET_METHOD}(self):\n"
        "    ops = self._registry()\n"
        f"    return tuple(ops{reads})\n",
        # a chain of aliases — the fixed point, not just the first hop
        f"def {TARGET_METHOD}(self):\n"
        "    a = self._operators()\n"
        "    b = a\n"
        f"    return tuple(b{reads})\n",
        # the walrus spelling
        f"def {TARGET_METHOD}(self):\n"
        f"    return tuple((ops := self._registry()){reads}) or ops\n",
    ):
        function = ast.parse(source).body[0]
        assert isinstance(function, ast.FunctionDef)
        problems = _violations(function, REPO_ROOT / "probe.py")
        assert problems, source

    # …and a legitimate `.keys()` read is not flagged, so the guard is a check
    # on the collapse rather than a ban on a method.
    benign = ast.parse(
        f"def {TARGET_METHOD}(self):\n"
        "    return tuple(self._declaration.required_operator_keys)\n"
    ).body[0]
    assert isinstance(benign, ast.FunctionDef)
    assert not _violations(benign, REPO_ROOT / "probe.py")
