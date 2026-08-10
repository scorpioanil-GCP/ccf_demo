"""D-06 — the orchestration/adapters module-tree split, lint-enforced.

D-IMPL-60 consequence (a): orchestrator-driver integrations live under
``runtime/ccf_runtime/orchestration/<sdk>/`` — never under
``runtime/ccf_runtime/adapters/<sdk>/`` — and the separate module tree is
the *structural* enforcement of D-IMPL-17's two-seam distinction (an SDK as
agent harness vs the same SDK as orchestrator of CCF workflows). This lint
is the enforcement: it bans imports **bidirectionally** between the two
trees, so advisory A7's failure mode — promoting an adapter's private
topology (e.g. the LangGraph adapter's ``_build_graph``) into a driver, or
a driver's engine plumbing into an adapter — is structurally
unrepresentable rather than merely documented.

One rule, one AST walk, in the house lint style (D-06 — stdlib ``ast``, no
plugin framework; D-07 — blocking, wired into ``python -m tools.lints
--all``):

``d06-orchestration-split``
    A module under ``ccf_runtime.orchestration.*`` may not import
    ``ccf_runtime.adapters`` or anything under it, and a module under
    ``ccf_runtime.adapters.*`` may not import ``ccf_runtime.orchestration``
    or anything under it. Both directions are explicit because each guards
    a different promotion path, and a one-directional ban would leave the
    other half of A7 available.

No allowlist, no carve-out: the two trees share exactly nothing. Anything
both need belongs in the engine's public surface or in ``/src`` contracts.

Both spellings of an import (review finding F0)
-----------------------------------------------

Both tree names are dotted, so both were reachable by a spelling this rule did
not see: ``from ccf_runtime import adapters`` inside a driver reported
``ccf_runtime`` under :func:`~tools.lints.imported_module_names`, which matches
no entry. Proven by execution, in **both** directions, before the fix — the
close-time panel's probe of this rule was inconclusive because it used a module
path outside the rule's own scope, so `check_source` returned early and the
result established nothing either way. The rule now resolves every name a
statement reaches through :func:`~tools.lints.reached_module_names`, which also
picks up the relative spellings (``from ..adapters import x``) both name
helpers used to drop.
"""

from __future__ import annotations

import ast
import pathlib

from tools.lints import (
    format_finding,
    matches_module,
    package_for,
    read_tree,
    reached_module_names,
)

RULE_SPLIT = "d06-orchestration-split"

#: The orchestrator-driver tree (D-IMPL-60 consequence (a)).
ORCHESTRATION_TREE: frozenset[str] = frozenset({"ccf_runtime.orchestration"})

#: The harness-adapter tree (CLAUDE.md §7.3; D-IMPL-53).
ADAPTER_TREE: frozenset[str] = frozenset({"ccf_runtime.adapters"})


def check_source(source: str, path: pathlib.Path, module_name: str) -> list[str]:
    """Check already-read `source` attributed to `path` / `module_name`."""
    tree = read_tree(source, path)
    findings: list[str] = []
    in_orchestration = matches_module(module_name, ORCHESTRATION_TREE)
    in_adapters = matches_module(module_name, ADAPTER_TREE)
    if not (in_orchestration or in_adapters):
        return findings

    package = package_for(path, module_name)
    denied_tree = ADAPTER_TREE if in_orchestration else ORCHESTRATION_TREE

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", 0)
        # One finding per import statement, not one per spelling it matches.
        denied = sorted(
            name
            for name in reached_module_names(node, package=package)
            if matches_module(name, denied_tree)
        )
        if not denied:
            continue
        name = denied[0]
        if in_orchestration:
            findings.append(
                format_finding(
                    path,
                    lineno,
                    RULE_SPLIT,
                    f"orchestration module {module_name!r} imports the"
                    f" adapter tree ({name!r}); drivers author their own"
                    " topology against the engine's public surface and"
                    " never reach adapter internals (D-IMPL-60, A7)",
                )
            )
        else:
            findings.append(
                format_finding(
                    path,
                    lineno,
                    RULE_SPLIT,
                    f"adapter module {module_name!r} imports the"
                    f" orchestration tree ({name!r}); the two seams are"
                    " separate module trees by ruling (D-IMPL-60,"
                    " D-IMPL-17)",
                )
            )

    return findings


def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
