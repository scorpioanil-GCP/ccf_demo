"""CINV-02 — the core never names a graph adapter (D-IMPL-93, property (1)).

CLAUDE.md §11 ("mechanism, not values") and §6.4 ("code contains interpreters
and factories, never the things interpreted"). SDK-defined enforcement
mechanism, not whitepaper-derived.

One rule, one AST walk:

``cinv02-backend-import``
    A module may import ``ccf.graph.backends`` or anything under it only if it
    is itself under ``ccf.graph.backends``. Before D-IMPL-93 the dependency
    arrow ran the wrong way: the composition root and the writer module each
    imported every adapter by name, which is what made the per-adapter cost of
    a new substrate nonzero and what made a substrate name unavoidable in core.
    After it, an adapter declares itself and the core resolves it through
    ``ccf.graph.registry``. This rule is what keeps the arrow turned around.

Why a sibling module rather than one more branch in ``harness_imports.py``
-------------------------------------------------------------------------

Two reasons, and the second is load-bearing for this phase.

First, precedent: ``tools/lints/orchestration_imports.py`` is this repository's
own answer to "where does an import rule live" — beside the harness checker,
not inside it, when it guards a different property.

Second, sequencing. This rule cannot be green until the plan that repoints the
composition root lands, and ``harness_imports`` is already registered in
``tools/lints/__main__.py``'s ``CHECKERS``. Putting the rule there would make
``make lint`` red for the rest of the phase — which is how a team learns to
read a red gate as normal. This module is deliberately *not* registered at
birth; the plan that makes the property true is the plan that turns the rule
on, so the first run over the tree is the first run that can pass.

D-IMPL-93 asks for the same *machinery*, not the same file, and this module
uses all of it: the shared AST walk, the four helpers in ``tools/lints``, the
``path:line rule message`` finding format, and the one exit-code contract.

No allowlist (D-13)
-------------------

No rule here takes an allowlist. Carve-outs are module-path constants in this
file, reviewed with the code, never a data file or per-module opt-out — a data
allowlist would void the invariant it exists to enforce. There are no
carve-outs today, and the exempt set is not a constant at all but the guarded
package itself: the adapters' own home.

What this rule cannot see
-------------------------

Stated rather than claimed away, in the voice ``src/ccf/boot.py`` uses for the
determined-insider residual.

An import lint reads ``import`` statements. ``ccf.graph.registry`` resolves the
adapter a deployment names with ``importlib.import_module``, and this walker
cannot see that call — a dynamically-constructed module name is not an
``ast.Import`` node and never will be. The claim strength here is therefore *no
unforced path exists*, never *no path exists*.

The compensating control is confinement, not detection: dynamic resolution
lives in one function in one module, and a test asserts that function is the
only ``import_module`` call site under **both** ``src/`` and ``runtime/`` — the
same two trees this rule is scoped to. Scoping the compensating control to one
package would have left a dynamic adapter import in the deployment wiring
invisible to the lint *and* to the test that exists to cover the lint's blind
spot.

Two smaller blind spots, for completeness. Relative imports carry no absolute
module name and are reported as nothing by
:func:`~tools.lints.imported_module_names`; ``src/`` uses none today, and a
relative import that reached across packages would have to climb out of its own
package to do it. And a module that depends on one adapter's *behaviour*
without importing it is beyond any import rule — that residual belongs to
``cinv04-substrate-name``, and past it, to review.

Both spellings of an import
---------------------------

``from ccf.graph import backends`` and ``from ccf.graph.backends import
sqlite_write`` reach the adapter package as surely as naming it in full, but
:func:`~tools.lints.imported_module_names` reports ``ccf.graph`` for the first
and only ``ccf.graph.backends`` for the second — correctly, since it cannot
tell a submodule from an attribute without importing, which a lint must not do.
The rule therefore resolves both forms through
:func:`~tools.lints.reached_module_names` (review finding CR-02). Two things
follow, and both are properties rather than details:

* ``from ccf.graph import backends`` is now caught. It was not before, which
  left a spelling of the exact import this rule exists to deny going unseen.
* The finding names the **most specific** module the statement reaches, so an
  adapter's write module is reported by its own name rather than by the package
  that contains it — and one import statement produces one finding, never one
  per spelling it happens to match.
"""

from __future__ import annotations

import ast
import pathlib

from tools.lints import (
    format_finding,
    matches_module,
    reached_module_names,
    read_tree,
)

RULE_BACKEND_IMPORT = "cinv02-backend-import"

#: The adapter package. Guarded from outside, unrestricted from inside: an
#: adapter may name its siblings freely, because inside this package a
#: substrate name is the module's whole subject.
BACKENDS_PACKAGE = "ccf.graph.backends"

#: The seam a core module uses instead. Named here so the finding message can
#: say what to do rather than only what not to.
REGISTRY_MODULE = "ccf.graph.registry"


def check_source(source: str, path: pathlib.Path, module_name: str) -> list[str]:
    """Check already-read `source` attributed to `path` / `module_name`."""
    tree = read_tree(source, path)
    findings: list[str] = []
    if matches_module(module_name, (BACKENDS_PACKAGE,)):
        return findings

    for node in ast.walk(tree):
        # Both spellings, and one finding per import statement rather than one
        # per spelling it matches — see the "Both spellings of an import"
        # section of the module docstring.
        denied = sorted(
            name
            for name in reached_module_names(node)
            if matches_module(name, (BACKENDS_PACKAGE,))
        )
        if not denied:
            continue
        # The most specific name the statement reaches, so the finding says
        # `ccf.graph.backends.sqlite_write` rather than the package that
        # merely contains it. Longest wins because a submodule name is its
        # package's name plus a dotted segment.
        name = max(denied, key=len)
        findings.append(
            format_finding(
                path,
                getattr(node, "lineno", 0),
                RULE_BACKEND_IMPORT,
                f"{module_name!r} imports the adapter module {name!r};"
                f" only modules under {BACKENDS_PACKAGE} may. An adapter"
                " registers itself and the core resolves the one a"
                f" deployment names through {REGISTRY_MODULE}. A core"
                " module that names an adapter is the dependency arrow"
                " D-IMPL-93 exists to reverse.",
            )
        )

    return findings


def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
