"""CINV-03 — Algorithmic - Semantic Alternation as a structural invariant.

CLAUDE.md §11 ("No hidden model calls in the algorithmic path") and whitepaper
§7.6.6. A module opts into the algorithmic side of the alternation with a
module-level dunder::

    __ccf_mode__ = "algorithmic"

The dunder is preferred over a docstring marker because it is trivially
AST-detectable and survives docstring edits (04-RESEARCH.md Pattern 6). A
tagged module may not import the LLM client Protocol (``ccf.llm``) or any
vendor model SDK, at module scope or deferred inside a function — LLMs never
see raw signal, and a lazily-imported client is still a model call in the
algorithmic path.

Like CINV-02 this checker takes no allowlist: an exempted algorithmic module is
simply a semantic module and should drop the tag.
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

RULE_ALGORITHMIC = "cinv03-algorithmic"

#: The module-level tag that puts a module on the algorithmic side.
MODE_DUNDER = "__ccf_mode__"
ALGORITHMIC_MODE = "algorithmic"

#: The single crisp SDK import target (the LLMClientProtocol home, D-IMPL-09)
#: plus the vendor SDKs a module might reach for to bypass it.
LLM_MODULES: frozenset[str] = frozenset(
    {
        "ccf.llm",
        "anthropic",
        "openai",
        "cohere",
        "litellm",
        "google.generativeai",
        "mistralai",
    }
)


def is_algorithmic(tree: ast.Module) -> bool:
    """True when the module carries ``__ccf_mode__ = "algorithmic"`` at top level."""
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(t, ast.Name) and t.id == MODE_DUNDER for t in targets
        ):
            continue
        value = node.value
        if isinstance(value, ast.Constant) and value.value == ALGORITHMIC_MODE:
            return True
    return False


def check_source(source: str, path: pathlib.Path, module_name: str) -> list[str]:
    """Check already-read `source` attributed to `path` / `module_name`."""
    tree = read_tree(source, path)
    if not is_algorithmic(tree):
        return []

    findings: list[str] = []
    for node in ast.walk(tree):
        for name in imported_module_names(node):
            if matches_module(name, LLM_MODULES):
                findings.append(
                    format_finding(
                        path,
                        getattr(node, "lineno", 0),
                        RULE_ALGORITHMIC,
                        f"module is tagged {MODE_DUNDER}={ALGORITHMIC_MODE!r} and"
                        f" may not import {name!r} — LLMs never see raw signal"
                        " (CLAUDE.md §11); move the model call to a semantic"
                        " stage",
                    )
                )
    return findings


def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
