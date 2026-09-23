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

__all__ = ["WrongTreeLoaded", "door_module_of"]

#: The bare package an example's egress door occupies. Every tree claims it.
DOOR_PACKAGE = "server"


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
