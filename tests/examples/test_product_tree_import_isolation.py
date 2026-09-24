"""`AIA-F-07` — a process holding one product tree must not execute another's.

**The defect class, stated once.** A CCF example product tree is imported by
BARE MODULE NAME off ``sys.path`` — ``produce``, ``deployment``,
``projection``, ``acquisition``, ``assembler``. Every tree occupies exactly
the same names, and **Python resolves a bare name from ``sys.modules`` before
it ever consults ``sys.path``**. So ``sys.path.insert(0, my_tree)`` followed by
``import produce`` binds whatever ``produce`` is already resident — silently,
and with no error unless the two trees happen to disagree about an attribute
name.

`AIA-F-07` found it at rung 22, where the lucky outcome was an
``AttributeError``. The dangerous outcome is the other one: two trees whose
producers share a function name — and this ladder names them alike on purpose
— bind cleanly and answer from **the wrong product**. A governance failure
wearing a successful answer.

**What this module holds, and why it is two tests and not one.**

The first is the repository-wide invariant: every shipped example module that
binds a product tree at import time is either an entry point that owns its
process, or it proves what it loaded. There is no third category, and a new
example that introduces one goes red here rather than at the moment two trees
first share a process.

The second exercises the one shipped path that is IMPORTED rather than run —
``examples/door-cp-05-credit-exposure-rollup/adapter.py`` — against a process
deliberately poisoned with another tree, **in a subprocess**, so the result
depends on nothing about collection order. Its negative control runs the same
poisoning with the guard removed and requires the wrong product to load: an
isolation test that passes because nothing was poisoned is not a test.
"""

from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys

from tests.examples import tree_import

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"

#: The bare names a product tree occupies. Any two trees claim all of them.
COLLIDING = frozenset(
    {"produce", "deployment", "projection", "acquisition", "assembler"}
)

#: The door that BINDS a frozen specimen it does not own, and the specimen it
#: must load. The only shipped module in the repository that is imported rather
#: than run, which is what makes it the one that can meet a second tree.
DOOR = EXAMPLES / "door-cp-05-credit-exposure-rollup"
SPECIMEN_NAME = "cp-05-credit-exposure-rollup"

#: A tree that is NOT the specimen, whose `produce` also defines `product` —
#: so a collision binds cleanly and raises nothing. That is the point.
INTRUDER = EXAMPLES / "cp-21-large-exposure"

def _module_level_tree_imports(path: pathlib.Path) -> frozenset[str]:
    """Which colliding bare names this module binds AT IMPORT TIME.

    Module level only: an import inside a function runs when the function
    runs, under whatever guard the function carries, and is not this check's
    subject.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover — a syntax error is another test's
        return frozenset()
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names} & COLLIDING
        elif isinstance(node, ast.ImportFrom) and node.module:
            found |= {node.module.split(".")[0]} & COLLIDING
    return frozenset(found)

def _binders() -> list[pathlib.Path]:
    """Modules that REACH FOR a tree — they put one on ``sys.path`` themselves.

    A tree's own siblings are excluded deliberately. `produce.py` does
    ``import deployment`` with no path work at all: it is loaded *by* a
    binder, inside whatever eviction that binder performed, and inherits its
    guarantee. Holding a sibling to this check would demand every module in
    every tree re-prove what its own entry point already established — and
    would make the check pass or fail on where a file sits rather than on
    what it does.
    """
    return sorted(
        path
        for path in EXAMPLES.rglob("*.py")
        if "__pycache__" not in path.parts
        and "sys.path" in path.read_text(encoding="utf-8")
        and _module_level_tree_imports(path)
    )

def test_every_shipped_binder_owns_its_process_or_proves_what_it_loaded() -> None:
    """`AIA-F-07`, repository-wide.

    Two safe shapes and no third:

    **owns its process** — the module carries an ``if __name__ == "__main__"``
    entry point. A `run.py` invoked as a program, or a `server/serve.py`
    spawned as a door, holds exactly one tree and cannot collide with another.

    **proves what it loaded** — the module compares the resolved
    ``__file__`` of what it imported against the tree it meant to import, and
    refuses rather than binding on a mismatch.

    Anything else binds a tree it cannot vouch for. The failure names the
    file, so a new example lands here rather than in a production process.
    """
    binders = _binders()
    assert binders, "no shipped binder was found at all; this check is vacuous"
    unguarded = []
    for path in binders:
        text = path.read_text(encoding="utf-8")
        owns_process = '__name__ == "__main__"' in text
        proves = "__file__" in text and "sys.modules.pop" in text
        if not (owns_process or proves):
            unguarded.append(str(path.relative_to(REPO_ROOT)))
    assert not unguarded, (
        "these shipped modules bind a product tree at import time, do not own"
        " their process, and do not prove what they loaded — so a resident"
        f" tree of another product binds instead (`AIA-F-07`): {unguarded}"
    )

#: The poisoning probe, run as a FILE in a fresh interpreter. A file rather
#: than an inline ``-c`` string because the guard-removal variant has to edit
#: the adapter's source, and an inline script that builds source by string
#: concatenation is how an indentation bug becomes a passing isolation test.
PROBE = pathlib.Path(__file__).with_name("_cp_import_isolation_probe.py")

def _probe(*mode: str) -> dict[str, str]:
    """Import the door's adapter in a fresh process that already holds another tree.

    A subprocess for two reasons. It cannot disturb this session's
    ``sys.modules``, and its result is independent of what pytest collected
    first — *"no collection-order workaround"* cuts both ways, and a check
    that only reproduces the collision under one ordering is one of them.
    """
    completed = subprocess.run(
        [sys.executable, str(PROBE), str(REPO_ROOT), str(DOOR), str(INTRUDER), *mode],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])

def test_the_door_loads_its_own_specimen_even_with_another_tree_resident() -> None:
    """`AIA-F-07` — the shipped guarded path, exercised.

    `examples/door-cp-05-credit-exposure-rollup/adapter.py` is the one shipped
    module in the repository that is *imported* rather than run, so it is the
    one that meets a second tree. It binds the frozen cp-05 specimen it exists
    to serve.

    **The negative control is the whole test.** With the guard removed and the
    identical poisoning applied, the adapter must bind the INTRUDER — because
    if it binds the specimen either way, this test is measuring nothing.

    Measured 2026-09-22 before the repair: with `cp-21-large-exposure`
    resident, the door bound cp-21's `produce`. cp-21's producer defines
    `product()` too, so no `AttributeError` surfaced — the door would have
    served the large-exposure product through the exposure rollup's door,
    correctly shaped and entirely wrong.
    """
    unguarded = _probe("unguarded")
    assert unguarded["resident"] == INTRUDER.name
    assert unguarded["loaded"] == INTRUDER.name, (
        "the negative control did not reproduce the collision, so this test"
        f" cannot show the guard does anything: {unguarded}"
    )

    guarded = _probe()
    assert guarded["resident"] == INTRUDER.name, "the poison did not take"
    assert guarded["outcome"] == "bound", guarded
    assert guarded["loaded"] == SPECIMEN_NAME, (
        "the door bound a product it does not serve while another tree was"
        f" resident (`AIA-F-07`): {guarded}"
    )

def test_the_door_refuses_rather_than_binding_a_tree_it_cannot_vouch_for() -> None:
    """`AIA-F-07` — the guard REFUSES; it does not fall back.

    Pointed at a specimen directory that holds no product tree, the adapter
    must raise rather than bind whatever happens to be resident. A guard that
    degrades to the ambient module on a mismatch is the original defect with
    an extra step.
    """
    result = _probe("empty-specimen")
    assert result["outcome"] != "bound", (
        "the door bound a module from outside the specimen it names rather"
        f" than refusing: {result}"
    )
    assert result["loaded"] != INTRUDER.name, result


# ---------------------------------------------------------------------------
# The `server.serve` namespace — `LEX-F-11`, and the third instance of it.
# ---------------------------------------------------------------------------

#: Two trees that both ship a door. Their door modules define DIFFERENT opener
#: names, which is what made the third instance surface as an AttributeError
#: rather than as a wrong answer.
DOOR_TREES = ("cp-21-large-exposure", "cp-24-portfolio-what-if")

#: Every test module that reaches an example's door by the bare `server` name.
DOOR_IMPORTERS = (
    "test_cp_17_doors.py",
    "test_cp_19_door.py",
    "test_cp_21_sabotage.py",
    "test_cp_24_sabotage.py",
)


def test_the_door_helper_beats_a_resident_foreign_door() -> None:
    """`LEX-F-11` / `AIA-F-07` in the door namespace, with its control.

    Measured 2026-09-22: `test_cp_24_sabotage` failed in the full suite and
    passed alone, bisected to ONE predecessor — `test_cp_21_sabotage` — with
    `module 'server.serve' has no attribute 'open_book_door'`. cp-21 evicts
    correctly on entry and leaves its own `server.serve` resident; cp-24 did
    not evict at all, so it bound cp-21's door.

    **The negative control is the point.** With one tree's door resident, a
    plain `from server import serve` must still return THAT tree's module —
    otherwise this test proves nothing about the helper that follows it.
    """
    first, second = (EXAMPLES / name for name in DOOR_TREES)
    saved = {
        name: sys.modules.pop(name, None)
        for name in [n for n in list(sys.modules) if n == "server" or n.startswith("server.")]
    }
    try:
        sys.path.insert(0, str(first))
        try:
            from server import serve as resident  # noqa: PLC0415
        finally:
            sys.path.remove(str(first))
        assert pathlib.Path(resident.__file__).parent.parent == first

        # THE CONTROL: unguarded, the second tree's import binds the FIRST
        # tree's module. If this ever stops being true the collision is gone
        # and the helper below is measuring nothing.
        sys.path.insert(0, str(second))
        try:
            from server import serve as unguarded  # noqa: PLC0415
        finally:
            sys.path.remove(str(second))
        assert pathlib.Path(unguarded.__file__).parent.parent == first, (
            "an unguarded import no longer inherits the resident door; the"
            " collision this helper exists for is not being reproduced"
        )

        # AND THE HELPER: same contaminated process, correct module.
        guarded = tree_import.door_module_of(second)
        assert pathlib.Path(guarded.__file__).parent.parent == second
    finally:
        for name in [n for n in list(sys.modules) if n == "server" or n.startswith("server.")]:
            del sys.modules[name]
        for name, module in saved.items():
            if module is not None:
                sys.modules[name] = module


def test_the_helper_refuses_rather_than_returning_a_foreign_door() -> None:
    """The helper RAISES on a mismatch; it does not fall back.

    A guard that degrades to the ambient module is the original defect with an
    extra step — and here the ambient module is another product's door, whose
    determination would then be compared as though it were this product's.
    """
    # cp-22 ships no door at all, so the helper cannot resolve one — and the
    # point is WHICH way it fails. `WrongTreeLoaded` is an `ImportError`, as is
    # the `ModuleNotFoundError` a doorless tree produces; either way nothing
    # foreign is returned. A fallback would hand back whatever `server.serve`
    # happened to be resident, which here is another product's door.
    with pytest.raises(ImportError):
        tree_import.door_module_of(EXAMPLES / "cp-22-agent-internal-assembly")


def test_every_door_importer_goes_through_the_one_helper() -> None:
    """Four importers, one home — so they cannot drift apart again.

    Two of the four had drifted when this was measured: `test_cp_19_door`
    evicted `server` without `server.serve` and never verified `serve`, and
    `test_cp_24_sabotage` did neither. A hand-rolled fourth copy is how the
    third instance of this defect was written.
    """
    for name in DOOR_IMPORTERS:
        source = (REPO_ROOT / "tests" / "examples" / name).read_text(encoding="utf-8")
        assert "tree_import.door_module_of" in source, (
            f"{name} reaches an example's door without the verifying helper"
        )
        # AST, not a substring: two of these modules describe the defect in
        # their own comments, and a grep would read the description as the
        # defect. The check is on what EXECUTES.
        bare = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom)
            and (node.module or "").split(".")[0] == "server"
        ]
        assert not bare, (
            f"{name} executes a bare `from server import ...` at line"
            f" {bare[0].lineno}; it binds whatever is resident (`LEX-F-11`)"
        )


# ---------------------------------------------------------------------------
# `AIA-F-07`, the dr-02 instance — the bare TOP-LEVEL names, not the door
# ---------------------------------------------------------------------------

#: The pair that reproduced it. `dr-02`'s substrate IS cp-06's product, so the
#: canonical suite reaches cp-06 first by ordinary dependency, not by accident.
DR02_TREE = EXAMPLES / "dr-02-package-a-context-product"
INTRUDER_TREE = EXAMPLES / "cp-06-canonical-collateral-and-setoff-coverage"

#: Run in a FRESH interpreter so the result depends on nothing about this
#: session's `sys.modules`. Two bindings are reported: what the UNGUARDED
#: import gives once the intruder is resident — the negative control, which
#: must bind the wrong tree or the poisoning proves nothing — and what
#: `tree_modules_of` gives under the same poisoning.
_DR02_PROBE = """
import json, pathlib, sys
repo, dr02, intruder = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
sys.path.insert(0, repo)

# Poison exactly as the canonical run does: the intruder's tree, imported
# by its bare name, resident first.
sys.path.insert(0, str(intruder))
import deployment as poisoned
sys.path.remove(str(intruder))

# THE NEGATIVE CONTROL. The old unguarded idiom, verbatim.
sys.path.insert(0, str(dr02))
import deployment as unguarded
sys.path.remove(str(dr02))

from tests.examples.tree_import import tree_modules_of
(guarded,) = tree_modules_of(dr02, "deployment")

print(json.dumps({
    "poisoned": str(pathlib.Path(poisoned.__file__).resolve().parent),
    "unguarded": str(pathlib.Path(unguarded.__file__).resolve().parent),
    "guarded": str(pathlib.Path(guarded.__file__).resolve().parent),
}))
"""


def test_the_unguarded_import_binds_the_wrong_tree_and_the_guarded_one_does_not() -> None:
    """`AIA-F-07` for `dr-02` — with its own negative control.

    `dr-02` passed alone and failed all nine gates in the canonical run,
    reproduced as `test_cp_06_mcp_door.py` then `test_dr_02_packaging.py`:
    its `produce` bound **cp-06's** `deployment` and died on `module
    'deployment' has no attribute 'acquire'`.

    **Both halves are asserted in one process.** A guarded import that passes
    while the unguarded one ALSO passes has proven nothing — it would mean the
    poisoning never took, and the guard was never the reason for the green.
    """
    import json  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    completed = subprocess.run(
        [sys.executable, "-c", _DR02_PROBE, str(REPO_ROOT), str(DR02_TREE), str(INTRUDER_TREE)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    seen = json.loads(completed.stdout.strip().splitlines()[-1])

    assert seen["poisoned"] == str(INTRUDER_TREE), seen
    # THE NEGATIVE CONTROL: the unguarded idiom binds the INTRUDER, because
    # Python resolves a bare name from `sys.modules` before `sys.path`.
    assert seen["unguarded"] == str(INTRUDER_TREE), (
        "the unguarded import bound the right tree, so this poisoning proves"
        f" nothing about the guarded one: {seen}"
    )
    # ...and the guard defeats exactly that.
    assert seen["guarded"] == str(DR02_TREE), seen


def test_the_three_colliding_rosters_agree() -> None:
    """One roster of bare names, stated in three places, held together here.

    `tree_import.COLLIDING_MODULES`, this module's `COLLIDING`, and the cp-05
    door adapter's `_COLLIDING` each name the bare modules a product tree
    occupies. Three copies drift, and a name missing from one of them is a
    name that tree does not evict — which is `AIA-F-07` returning through the
    one roster nobody updated.
    """
    import ast  # noqa: PLC0415

    from tests.examples.tree_import import COLLIDING_MODULES  # noqa: PLC0415

    adapter = (EXAMPLES / "door-cp-05-credit-exposure-rollup" / "adapter.py").read_text(
        encoding="utf-8"
    )
    declared: set[str] | None = None
    for node in ast.walk(ast.parse(adapter)):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_COLLIDING" for t in node.targets
        ):
            declared = {ast.literal_eval(e) for e in node.value.elts}  # type: ignore[attr-defined]
    assert declared is not None, "the cp-05 door adapter no longer declares `_COLLIDING`"
    assert set(COLLIDING_MODULES) == COLLIDING == declared, (
        sorted(COLLIDING_MODULES),
        sorted(COLLIDING),
        sorted(declared),
    )
