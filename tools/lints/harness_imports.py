"""CINV-02 — zero harness imports in core, plus the GraphWriter restriction.

CLAUDE.md §7.3 ("Zero harness imports in core") and §10 (single-writer
invariant). SDK-defined enforcement mechanism, not whitepaper-derived.

Two rules, one AST walk:

``cinv02-harness``
    Lint-enforced: no module outside ``ccf_runtime.adapters.*`` may import a
    harness package. A harness import in ``/src`` is a defect of the same class
    as an LLM client in an algorithmic module. The vendor LLM SDK
    (``anthropic``) is on the deny list everywhere *except* the LLM adapter
    path, where it is the adapter's whole purpose (D-IMPL-09).

``cinv02-graph-writer``
    The concrete writer module ``ccf.graph._writer`` is importable only from L2
    (``ccf.assembly``) and the composition root (``ccf.boot``). This is layer 2
    of the single-writer defence: even with a writer implementation on disk, no
    other module can name it.

Scope, stated precisely (D-21 — claims are scoped to their enforcement).
``cinv02-harness`` is lint-enforced as: *no module outside
``ccf_runtime.adapters.*`` may import a harness package*. That narrows the
rule's scope to match CLAUDE.md §7.3's own word — "zero harness imports in
**core**" — rather than granting an exception to it; the adapter path is where
§7.3 places harness bindings, so a harness import there is the module's whole
purpose (D-IMPL-53, D-24).

Neither rule takes an allowlist. Carve-outs are module-path constants in this
file, reviewed with the code, never a data file or per-module opt-out — a
data allowlist would void the invariant it exists to enforce.
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

RULE_HARNESS = "cinv02-harness"
RULE_GRAPH_WRITER = "cinv02-graph-writer"

#: Agent harnesses the SDK must never import. CCF layers onto a harness as the
#: trust-and-control plane; it never absorbs the loop (CLAUDE.md §7.3).
HARNESS_DENY: frozenset[str] = frozenset(
    {"google.adk", "langgraph", "claude_agent_sdk"}
)

#: Vendor LLM SDKs, permitted only inside the LLM adapter path below.
VENDOR_LLM_DENY: frozenset[str] = frozenset({"anthropic"})

#: Modules allowed to import a vendor LLM SDK (the LLMClientProtocol adapters).
LLM_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf.llm", "ccf_runtime.llm"})

#: The only module path where a harness import is the module's whole purpose:
#: the HarnessAdapterProtocol reference adapters, which CLAUDE.md §7.3 places in
#: ``runtime/adapters/<harness>/``. Match is dot-bounded, so ``adapters_evil``
#: and every other sibling remain denied.
HARNESS_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf_runtime.adapters"})

#: The concrete GraphWriter module and its permitted importers.
WRITER_MODULE = "ccf.graph._writer"
WRITER_OK_MODULES: frozenset[str] = frozenset({"ccf.assembly", "ccf.boot"})


def check_source(source: str, path: pathlib.Path, module_name: str) -> list[str]:
    """Check already-read `source` attributed to `path` / `module_name`."""
    tree = read_tree(source, path)
    findings: list[str] = []
    in_llm_adapter = matches_module(module_name, LLM_ADAPTER_MODULES)
    in_harness_adapter = matches_module(module_name, HARNESS_ADAPTER_MODULES)

    for node in ast.walk(tree):
        for name in imported_module_names(node):
            lineno = getattr(node, "lineno", 0)
            if matches_module(name, HARNESS_DENY) and not in_harness_adapter:
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_HARNESS,
                        f"harness import {name!r} is forbidden in core"
                        " (CLAUDE.md §7.3); bind harnesses in"
                        " runtime/adapters/<harness>/ instead",
                    )
                )
            elif matches_module(name, VENDOR_LLM_DENY) and not in_llm_adapter:
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_HARNESS,
                        f"vendor LLM import {name!r} is allowed only inside the"
                        " LLMClientProtocol adapter path"
                        f" ({', '.join(sorted(LLM_ADAPTER_MODULES))})",
                    )
                )
            if matches_module(name, (WRITER_MODULE,)) and not matches_module(
                module_name, WRITER_OK_MODULES
            ):
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_GRAPH_WRITER,
                        f"GraphWriter module {name!r} is importable only from"
                        f" {', '.join(sorted(WRITER_OK_MODULES))}"
                        f" (single-writer invariant, CLAUDE.md §10);"
                        f" {module_name!r} may not name it",
                    )
                )

    return findings


def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
