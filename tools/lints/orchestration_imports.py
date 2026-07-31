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
"""

from __future__ import annotations

import ast
import pathlib

from tools.lints import (
    format_finding,
    imported_module_names,
    matches_module,
    read_tree,
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

    for node in ast.walk(tree):
        for name in imported_module_names(node):
            lineno = getattr(node, "lineno", 0)
            if in_orchestration and matches_module(name, ADAPTER_TREE):
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
            elif in_adapters and matches_module(name, ORCHESTRATION_TREE):
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
