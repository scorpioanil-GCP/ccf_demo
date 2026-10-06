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

Model endpoints over raw HTTP (LOW-05, D-IMPL-372)
---------------------------------------------------

An import denylist cannot see a model call made with a general HTTP client:
measured before this rule, a tagged module doing
``httpx.post("https://api.anthropic.com/v1/messages", ...)`` produced no
finding. A second rule, :data:`RULE_MODEL_ENDPOINT`, therefore reads every
**string or bytes constant** in a tagged module — f-string parts included,
because an ``ast.JoinedStr`` holds its literal parts as constants — and refuses
one containing any of :data:`MODEL_ENDPOINT_FRAGMENTS`, case-insensitively.
The fragments are only ever model-endpoint spellings (vendor paths and
hosts), so a URL concatenated from pieces is still caught by whichever piece
carries one (``"https://bedrock-runtime.<region>.amazonaws.com/model/" + M``).

It never flags the HTTP import itself: several algorithmic modules import
``httpx`` or ``urllib`` to reach graph stores, peers and MCP servers, which is
legitimate, and an import rule would refuse all of them. Docstrings are exempt
— a docstring is prose about a call, never a call. This rule takes no
allowlist either.

**What a static lint cannot see**, stated so nobody infers otherwise: a URL
read from configuration, an environment variable or a network response, or one
assembled entirely from fragments none of which is a model-endpoint spelling.
Those are deployment-review concerns; the rule's acceptance is the literal and
fragment cases.

Both spellings of an import (review finding F0)
-----------------------------------------------

Two entries in :data:`LLM_MODULES` carry a dot — ``ccf.llm`` and
``google.generativeai`` — and both were reachable by a spelling this rule did
not see. Proven by execution before the fix: in a module tagged
``__ccf_mode__ = "algorithmic"``, ``from ccf.llm import LLMClient`` produced a
finding and ``from ccf import llm`` produced none, which is the SDK's *own*
LLM seam entering the algorithmic path unremarked. The single-segment vendor
entries (``anthropic``, ``openai``, ``cohere``, ``litellm``, ``mistralai``)
were never affected — they have no parent to be named by — and that asymmetry
is exactly what let the hole survive a suite that tests the vendor spellings.
The rule now reads :func:`~tools.lints.reached_module_names`, which resolves
the parent-named form and the relative form alike.
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

RULE_ALGORITHMIC = "cinv03-algorithmic"

#: The rule id for a model endpoint named in a tagged module's constants.
RULE_MODEL_ENDPOINT = "cinv03-model-endpoint"

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


#: Lower-case fragments that only ever spell a model endpoint: vendor API paths
#: and hosts (LOW-05). Matched as substrings of a lower-cased constant.
MODEL_ENDPOINT_FRAGMENTS: tuple[str, ...] = (
    "/v1/messages",
    "/chat/completions",
    "/v1/responses",
    ":generatecontent",
    ":streamgeneratecontent",
    "/invoke-model",
    "bedrock-runtime",
    "api.anthropic.com",
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "aiplatform.googleapis.com",
)


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """``id()`` of every docstring constant (module, class, function)."""
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            exempt.add(id(body[0].value))
    return exempt


def _endpoint_fragment(value: object) -> str | None:
    """The first model-endpoint fragment ``value`` contains, if it is text."""
    if isinstance(value, bytes):
        value = value.decode("latin-1")
    if not isinstance(value, str):
        return None
    lowered = value.lower()
    for fragment in MODEL_ENDPOINT_FRAGMENTS:
        if fragment in lowered:
            return fragment
    return None


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
    package = package_for(path, module_name)
    for node in ast.walk(tree):
        # One finding per import statement, not one per spelling it matches.
        denied = sorted(
            name
            for name in reached_module_names(node, package=package)
            if matches_module(name, LLM_MODULES)
        )
        if not denied:
            continue
        findings.append(
            format_finding(
                path,
                getattr(node, "lineno", 0),
                RULE_ALGORITHMIC,
                f"module is tagged {MODE_DUNDER}={ALGORITHMIC_MODE!r} and"
                f" may not import {denied[0]!r} — LLMs never see raw signal"
                " (CLAUDE.md §11); move the model call to a semantic"
                " stage",
            )
        )
    exempt = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or id(node) in exempt:
            continue
        fragment = _endpoint_fragment(node.value)
        if fragment is None:
            continue
        findings.append(
            format_finding(
                path,
                getattr(node, "lineno", 0),
                RULE_MODEL_ENDPOINT,
                f"module is tagged {MODE_DUNDER}={ALGORITHMIC_MODE!r} and"
                f" names a model endpoint ({fragment!r}) — a model call over"
                " raw HTTP is still a model call in the algorithmic path"
                " (CLAUDE.md §11); move it to a semantic stage",
            )
        )
    return findings


def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
