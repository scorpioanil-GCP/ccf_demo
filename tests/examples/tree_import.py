"""Import one example tree's door module, and PROVE it is that tree's.

**NOT A TEST MODULE.** A helper the example test modules import; pytest
collects nothing from it. `estate_guard.py` is the precedent for a shared
non-test helper living here.

**The defect this closes, stated once.** An example's egress door lives at
``<tree>/server/serve.py`` and is reached by the BARE package name ``server``.
Every tree occupies that name, and Python resolves a bare name from
``sys.modules`` before it consults ``sys.path`` — so
``sys.path.insert(0, my_tree)`` followed by ``from server import serve`` binds
whatever ``server.serve`` is already resident.

Two instances are on record and they are the same defect:

``LEX-F-11`` (cp-21)
    passed alone, failed in the full suite with *"module 'server.serve' has no
    attribute 'open_large_exposure_door'"*. Popping only the ``server``
    PACKAGE re-imports the package from the new path while ``from server
    import serve`` short-circuits on the stale SUBMODULE.

``AIA-F-07`` (cp-22)
    the same collision in the ``produce``/``deployment`` namespace, and the
    entry that made this a repository sweep.

**And a third, measured 2026-09-22 on the release-hardening pass.**
``test_cp_24_sabotage::test_the_scenario_crosses_the_door_unchanged`` failed in
the full suite and passed alone. Bisected to ONE predecessor —
``test_cp_21_sabotage`` — with the signature *"module 'server.serve' has no
attribute 'open_book_door'"*. cp-21 evicts correctly on entry but leaves its
own ``server.serve`` resident; cp-24 did not evict at all, so it bound cp-21's
door and called a method cp-21's door does not have.

**The attribute error is the lucky outcome, every time.** Two trees whose
doors shared a symbol name would have opened the wrong product's door and
compared its determination as though it were their own.

**Why eviction on ENTRY is the whole fix, and restoration is not needed.** If
every consumer evicts before importing, none can inherit a stale module —
whatever the previous one left behind, and in any collection order. Restoring
afterwards would be strictly worse here: a door module can import siblings
lazily, and unwinding the path under it is how the cp-05 door adapter was
measured booting and then failing every served question.

**This is not blanket-clearing in a harness.** The eviction is what makes the
verification meaningful in a contaminated process; the verification is what
makes the result trustworthy. A module that resolves outside the requested
tree raises rather than being used.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

__all__ = ["WrongTreeLoaded", "door_module_of", "tree_modules_of"]

#: The bare package an example's egress door occupies. Every tree claims it.
DOOR_PACKAGE = "server"

#: The bare TOP-LEVEL names a product tree occupies. Any two trees claim
#: exactly these, which is why :func:`tree_modules_of` evicts them rather than
#: assuming them absent. Kept in step with
#: `examples/door-cp-05-credit-exposure-rollup/adapter.py::_COLLIDING` and
#: `tests/examples/test_product_tree_import_isolation.py::COLLIDING`, and
#: `test_the_three_colliding_rosters_agree` is what holds the three together.
COLLIDING_MODULES: tuple[str, ...] = (
    "produce",
    "deployment",
    "projection",
    "acquisition",
    "assembler",
)


class WrongTreeLoaded(ImportError):
    """A module was loaded that does not live in the tree that was asked for."""


def _evict_door_package() -> None:
    """Drop the ``server`` package AND every submodule under it.

    Popping only ``server`` is `LEX-F-11`'s exact defect: the package
    re-imports from the new path while ``from server import serve``
    short-circuits on the stale ``server.serve`` still in ``sys.modules``.
    """
    stale = [
        name
        for name in sys.modules
        if name == DOOR_PACKAGE or name.startswith(f"{DOOR_PACKAGE}.")
    ]
    for name in stale:
        del sys.modules[name]


def door_module_of(example: pathlib.Path) -> Any:
    """Return ``<example>/server/serve.py`` as a module, proven to be that tree's.

    Args:
        example: The example tree's own directory — the one whose door is
            wanted. Its ``server/serve.py`` must exist.

    Returns:
        The imported ``server.serve`` module, verified to live under
        ``example``.

    Raises:
        WrongTreeLoaded: the import resolved outside ``example``. Raised rather
            than returned, because a test that opens another product's door and
            compares the answer as its own is the failure this helper exists to
            make impossible.
    """
    example = example.resolve()
    _evict_door_package()
    sys.path.insert(0, str(example))
    try:
        from server import serve as door  # noqa: PLC0415
    finally:
        sys.path.remove(str(example))

    resolved = pathlib.Path(door.__file__ or "").resolve()
    if resolved.parent.parent != example:
        raise WrongTreeLoaded(
            f"asked for {example.name}'s door and loaded {resolved}, which is"
            " outside that tree — another example's `server.serve` was resident"
            " and the eviction did not take (`LEX-F-11`, `AIA-F-07`)"
        )
    return door


def tree_modules_of(example: pathlib.Path, *names: str) -> tuple[Any, ...]:
    """Import an example tree's TOP-LEVEL modules, proven to be that tree's.

    :func:`door_module_of`'s sibling for the other half of `AIA-F-07`. That
    one covers the ``server`` PACKAGE; this covers the bare top-level names —
    ``produce``, ``deployment``, ``projection``, ``acquisition`` — which every
    tree occupies and which Python resolves from ``sys.modules`` before it
    consults ``sys.path``.

    **The measured instance this closes.** `dr-02` passed alone and failed
    every one of its nine gates in the canonical full run, reproduced in one
    command as ``test_cp_06_mcp_door.py`` then ``test_dr_02_packaging.py``:
    dr-02's own ``produce`` imported **cp-06's** ``deployment`` and died on
    ``module 'deployment' has no attribute 'acquire'``. The attribute error is
    the lucky outcome — cp-05's door bound cp-21's ``produce``, whose
    ``product()`` exists, and would have answered correctly shaped and
    entirely wrong.

    The shape is `examples/door-cp-05-credit-exposure-rollup/adapter.py`'s
    ``_specimen_modules`` lifted into the shared helper, unchanged in
    substance: **evict the colliding names, insert, import, verify the file
    that loaded lives in the tree that was asked for.**

    **The eviction is bounded to** :data:`COLLIDING_MODULES`. It is not a
    blanket purge: a name outside that roster is never touched, and the
    verification — not the eviction — is what makes the result trustworthy.

    **On success the tree STAYS resident and STAYS on ``sys.path``.** Measured
    2026-09-22 on cp-05: a version that restored afterwards booted, announced
    READY, and then failed every served question, because a tree's modules
    import their siblings lazily and unwinding the path leaves those later
    imports resolving somewhere else. What was displaced is put back only when
    the import FAILS.

    Args:
        example: The tree's own directory.
        names: The bare module names to import, in the order wanted.

    Returns:
        The imported modules, in the order named.

    Raises:
        WrongTreeLoaded: something resolved outside ``example``. Raised rather
            than returned — a test that runs another product's deployment and
            reports the answer as its own is the failure this prevents.
    """
    example = example.resolve()

    # Evict only what is FOREIGN. A resident module that already resolves
    # inside `example` is this tree's own and is returned as-is, because
    # re-importing would mint a SECOND module object for one file: a test that
    # patched `deployment.packager` and then asked a question through
    # `produce` would be patching an object the deployment no longer holds.
    # Measured — three dr-02 gates went red on an evict-always version, and
    # they were the three that carry their sabotage inside the test.
    saved: dict[str, Any] = {}
    for name in COLLIDING_MODULES:
        resident = sys.modules.get(name)
        if resident is None:
            continue
        home = pathlib.Path(getattr(resident, "__file__", "") or "").resolve().parent
        if home != example:
            saved[name] = sys.modules.pop(name)

    if str(example) not in sys.path:
        sys.path.insert(0, str(example))
    try:
        loaded = tuple(__import__(name) for name in names)
        for module in loaded:
            resolved = pathlib.Path(module.__file__ or "").resolve().parent
            if resolved != example:
                raise WrongTreeLoaded(
                    f"asked for {example.name}'s `{module.__name__}` and"
                    f" loaded {resolved}, which is outside that tree — another"
                    " example's module was resident and the eviction did not"
                    " take (`AIA-F-07`)"
                )
        return loaded
    except BaseException:
        if str(example) in sys.path:
            sys.path.remove(str(example))
        for name, module in saved.items():
            if module is not None:
                sys.modules[name] = module
        raise
