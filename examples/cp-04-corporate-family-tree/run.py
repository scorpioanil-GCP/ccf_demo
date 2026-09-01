"""The in-process caller — A PLACEHOLDER UNTIL PLAN ``24.4-08`` AUTHORS IT.

WHY THIS FILE EXISTS AT WAVE 3 RATHER THAN AT WAVE 6
----------------------------------------------------

``tests/examples/test_artifact_schema_headers.py`` closes a **two-sided
bijection** over the examples tree: every example root has an ``artifacts/``
directory the ``$schema`` header gate covers, and every covered ``artifacts/``
directory sits directly under an example root. An *example root* is defined
mechanically, at ``EXAMPLE_ROOT_MARKER``, as **a directory that directly
contains a file named** ``run.py``.

Plan ``24.4-03`` creates ``examples/cp-04-corporate-family-tree/artifacts/``.
Plan ``24.4-08`` creates this example's ``run.py``. Between the two — plans
04, 05, 06 and 07 — the artifacts directory is covered by the header gate while
its parent is not yet an example root, and
``test_every_covered_artifact_directory_sits_under_an_example_root`` fails by
name:

    covered `artifacts/` directories whose parent is not an example root
    (no `run.py` beside them): cp-04-corporate-family-tree/artifacts

That was **measured, not anticipated** — the suite was green before this plan's
first artifact landed and red immediately after — and it is a sequencing defect
in the phase's wave order rather than anything wrong with the gate. **The gate
is not weakened, narrowed, or exempted to accommodate it.** It keeps its
definition and its full strength; this file supplies the thing the definition
asks for.

WHAT THIS FILE IS NOT
---------------------

It is **not** the caller. It runs nothing, assembles nothing and serves
nothing, because nothing it would call exists yet:
``deployment.py`` arrives at plan ``24.4-06`` and ``assembler.py`` at
``24.4-07``. It refuses, loudly, naming the plan that replaces it.

**Plan ``24.4-08`` OVERWRITES this module in full.** It is a placeholder with a
named owner and a named replacement, not a partial implementation to be built
on: nothing below is a design decision, and no later plan should preserve any
of it.

Importing this module has no side effects, so a collector that imports every
``.py`` under ``examples/`` sees a module that does nothing rather than one
that raises at import time.
"""

from __future__ import annotations

import sys

#: The plan that replaces this module in full.
REPLACED_BY = "24.4-08"

#: Named so the refusal is greppable and so the message and this constant
#: cannot drift apart.
REFUSAL = (
    "examples/cp-04-corporate-family-tree/run.py is a PLACEHOLDER."
    f" The in-process caller is authored by plan {REPLACED_BY};"
    " deployment.py arrives at 24.4-06 and assembler.py at 24.4-07."
    " This file exists from wave 3 only so the example-root bijection in"
    " tests/examples/test_artifact_schema_headers.py stays true while the"
    " artifacts directory is covered by the $schema header gate — see this"
    " module's docstring. It runs nothing."
)


def main() -> int:
    """Refuse, and say what is missing and who supplies it."""
    print(REFUSAL, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
