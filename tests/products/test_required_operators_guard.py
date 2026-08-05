"""G-B — no projection derives `required_operators()` from the registry's keys.

Plan 15-13 changed `examples/00-quickstart`'s `QuickstartPlan.required_operators()`
to declare its keys from the `ccf.product-class` artifact rather than return
`operators.keys()`, and 15-14 through 15-20 carried the same change through the
rest of the suite. **That closes the instances. It does not close the pattern.**

Why the shortcut is a governance defect and not a style one
------------------------------------------------------------

Gate 2 — lineage strict equality, whitepaper §7.6, INV-CH7-47 — compares what
the producer *declared* against what the projection engine *observed itself
running*. It is a real check only because those two values arrive from two
independent mechanisms.

`required_operators()` sits on the declaring side. A projection returning the
operator registry's own `keys()` makes the plan "declare" precisely what the
engine resolved, so the comparison Gate 2 performs is a value against itself.
It stays green. The invariant is gone, and nothing fails to say so.

That is the same collapse `tests/products/test_gate_independence.py` exists to
prevent, one level up: that module stops a *helper* deriving both sides from one
input; this module stops a *projection* doing it.

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
for the same two reasons: a source-text grep is defeated by a rename
(`registry.keys()`, `ops.keys()`) and is fooled by a comment or a docstring that
merely *mentions* `operators.keys()` — including this module's own.

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
SCANNED_TREES: tuple[str, ...] = ("src", "runtime", "examples")

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
    ``_registry``; anything with no identifier at its root yields ``None``.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _receiver_name(node.func)
    return None


def _violations(
    function: ast.FunctionDef | ast.AsyncFunctionDef, path: pathlib.Path
) -> list[str]:
    """Every `<registry>.keys` read inside one `required_operators` body."""
    parameters = {
        argument.arg
        for argument in (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
        if argument.arg != "self"
    }
    refused = REGISTRY_RECEIVERS | parameters

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
            " The projection's DECLARATION and the engine's RESOLUTION must"
            " remain two independent mechanisms, because Gate 2 (lineage"
            " strict equality, whitepaper §7.6, INV-CH7-47) compares them."
            " Reading the registry's own keys here makes that comparison a"
            " value against itself: it passes, and the invariant is gone with"
            " nothing failing to say so. Declare the keys from the"
            " `ccf.product-class` artifact's `required_operator_keys` instead."
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
    """G-B, closed structurally rather than instance by instance."""
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
        f"def {TARGET_METHOD}(self, operators):\n"
        f"    return frozenset(operators{reads})\n",
        f"def {TARGET_METHOD}(self):\n"
        f"    return tuple(self._registry(){reads})\n",
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
