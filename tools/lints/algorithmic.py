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
**string-valued expression** in a tagged module and refuses one containing any
of :data:`MODEL_ENDPOINT_FRAGMENTS`, case-insensitively. The fragments are only
ever model-endpoint spellings (vendor paths and hosts).

The expression is **constant-folded before it is matched** (the close panel's
LOW-05 finding: ``"https://" + "api." + "anthropic.com" + "/v1/" + "messages"``
drew no finding when each literal was matched alone). See :func:`_fold`:

* a ``+`` chain whose leaves are str/bytes literals is matched as one joined
  string;
* an f-string is matched as one string — its literal parts joined across the
  whole f-string, an interpolated literal or known name folded in, any other
  interpolation standing in as an opaque placeholder;
* a name is folded to its value when a **simple straight-line assignment** in
  the same scope bound it earlier in source order (``NAME = <foldable>``,
  ``NAME = NAME + "<lit>"``, ``NAME += "<lit>"``), or, inside a function, when
  the module bound it. One level of scope: module, then each function with the
  module's final bindings. Assignments inside ``if``/``for``/``with``/``try``
  are not followed and invalidate the name — there is no control-flow analysis.

The match is taken on the **largest** foldable expression only, so one URL is
one finding wherever its pieces sit.

It never flags the HTTP import itself: several algorithmic modules import
``httpx`` or ``urllib`` to reach graph stores, peers and MCP servers, which is
legitimate, and an import rule would refuse all of them. Docstrings are exempt
— a docstring is prose about a call, never a call. This rule takes no
allowlist either.

**What a static lint cannot see**, stated so nobody infers otherwise: a URL
assembled at runtime from configuration, an environment variable, a network
response, or any non-literal computation (a function call, a ``join``, a
``format``, a value threaded through a parameter, an attribute or a container,
an assignment under control flow). Those are deployment-review concerns, not
something this rule claims to cover.

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


#: What an interpolation the folder cannot resolve contributes to a folded
#: f-string: a character no endpoint fragment contains, so it can neither
#: complete nor be mistaken for a fragment.
_OPAQUE = "\x00"

#: A scope's straight-line bindings: name -> folded text.
_Env = dict[str, str]


def _fold(node: ast.AST, env: _Env) -> str | None:
    """The text ``node`` evaluates to, if it is a foldable literal expression."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bytes):
            return node.value.decode("latin-1")
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _fold(node.left, env)
        right = _fold(node.right, env)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                inner = None
                if value.conversion == -1 and value.format_spec is None:
                    inner = _fold(value.value, env)
                parts.append(_OPAQUE if inner is None else inner)
            else:
                parts.append(_fold(value, env) or "")
        return "".join(parts)
    return None


def _scope_bodies(tree: ast.Module) -> list[list[ast.stmt]]:
    """The module body first, then every function body in the module."""
    bodies: list[list[ast.stmt]] = [tree.body]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bodies.append(node.body)
    return bodies


def _scope_nodes(stmt: ast.stmt) -> list[ast.AST]:
    """Every node of ``stmt`` that belongs to its scope (no nested functions)."""
    found: list[ast.AST] = []
    pending: list[ast.AST] = [stmt]
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Decorators and defaults evaluate in this scope; the body is its
            # own scope, read by ``_folded_expressions`` separately.
            pending.extend(node.decorator_list)
            pending.extend(node.args.defaults)
            pending.extend(d for d in node.args.kw_defaults if d is not None)
            continue
        found.append(node)
        pending.extend(ast.iter_child_nodes(node))
    return found


def _bind(stmt: ast.stmt, env: _Env) -> None:
    """Apply ``stmt``'s simple straight-line bindings to ``env``, in place."""
    if isinstance(stmt, ast.Assign):
        value = _fold(stmt.value, env)
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                if value is None:
                    env.pop(target.id, None)
                else:
                    env[target.id] = value
        return
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        value = None if stmt.value is None else _fold(stmt.value, env)
        if value is None:
            env.pop(stmt.target.id, None)
        else:
            env[stmt.target.id] = value
        return
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
        held = env.get(stmt.target.id)
        tail = _fold(stmt.value, env)
        if isinstance(stmt.op, ast.Add) and held is not None and tail is not None:
            env[stmt.target.id] = held + tail
        else:
            env.pop(stmt.target.id, None)
        return
    # A name bound under control flow, by a loop, ``with``, import or walrus is
    # not followed: forget it rather than keep a value it may no longer hold.
    for node in _scope_nodes(stmt):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            env.pop(node.id, None)


def _folded_expressions(tree: ast.Module, exempt: set[int]) -> list[tuple[ast.AST, str]]:
    """Every maximal foldable str expression, with its folded text, by scope."""
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    module_env: _Env = {}
    results: list[tuple[ast.AST, str]] = []
    for index, body in enumerate(_scope_bodies(tree)):
        env: _Env = module_env if index == 0 else dict(module_env)
        for stmt in body:
            for node in _scope_nodes(stmt):
                if id(node) in exempt or not isinstance(
                    node, (ast.Constant, ast.BinOp, ast.JoinedStr)
                ):
                    continue
                text = _fold(node, env)
                if text is None:
                    continue
                parent = parents.get(id(node))
                if isinstance(parent, ast.JoinedStr | ast.FormattedValue):
                    continue  # matched as part of the whole f-string
                if (
                    isinstance(parent, ast.BinOp)
                    and isinstance(parent.op, ast.Add)
                    and _fold(parent, env) is not None
                ):
                    continue  # matched as part of the larger chain
                results.append((node, text))
            _bind(stmt, env)
    return results


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
    for node, text in _folded_expressions(tree, exempt):
        fragment = _endpoint_fragment(text)
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
