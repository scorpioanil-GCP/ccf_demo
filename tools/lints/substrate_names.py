"""CINV-04 — no substrate name in core (D-IMPL-93, property (2)).

CLAUDE.md §11 ("mechanism, not values") and §6.4 ("code contains interpreters
and factories, never the things interpreted"). SDK-defined enforcement
mechanism, not whitepaper-derived.

``cinv02-backend-import`` (``tools/lints/backend_imports.py``) stops core
*importing* an adapter. It does not stop core *naming* one, and naming is how
the coupling actually shows up: a keyword argument per database, a six-name
``Literal``, a mapping from substrate to required setting, and — the half that
no gate has ever caught — a docstring sentence enumerating every backend, which
has to be edited once per substrate forever. D-GATE-15.3 counted seventeen
deletions of exactly that shape in one phase. This module is the other half of
the property.

Two rule ids under one AST walk:

``cinv04-substrate-name``
    A substrate name appears in a *code* position — a non-docstring string
    literal, a bare name, an attribute, a parameter, a ``def``/``class`` name,
    or an import alias.

``cinv04-substrate-prose``
    One docstring enumerates :data:`PROSE_DISTINCT_THRESHOLD` or more *distinct*
    substrate names. Prose that lists the adapters is per-adapter prose: it is
    correct only until the next adapter, and its cost is paid on every one.

The vocabulary is derived, never typed
--------------------------------------

:func:`substrate_vocabulary` reads the stems of ``*.py`` under the adapter
package on disk, drops ``__init__``, and strips a trailing write-module suffix.
That is CLAUDE.md §11 turned on the checker itself: this module holds an
interpreter, not a list. A seventh adapter file extends the ban the moment it
lands, with no edit here — and the rule cannot drift out of step with the set of
adapters it is about, because there is only one set.

Sub-rule 2a — code positions
----------------------------

Matching is by the word-boundary pattern ``(?i)(?<![a-z0-9])<name>(?![a-z0-9])``.
The boundary is deliberately loose: it treats ``_`` as a boundary character, so
``<name>_dsn`` and ``<name>_uri`` match. Tightening it to exclude ``_`` on both
sides was measured and does clear the single residual on today's tree — but it
also stops the rule catching a reintroduced ``<name>_dsn`` parameter, which is
the exact thing the rule exists to catch. The residual is handled in the scope
constant below instead, where it is visible.

Sub-rule 2b — docstring enumeration
-----------------------------------

Docstrings are identified *structurally* — the first statement of a module,
class or function body when it is a string constant — never by position in the
file text, so a module-level string that merely looks like prose is scanned as a
literal by 2a rather than exempted as a docstring.

The threshold has a measured step of margin. Across core today every docstring
naming three or more substrates is in a file this phase reshapes, and every
*legitimate* comparative docstring — a note about precision drift between two
stores, a note about two vector indices agreeing on a distance metric — names at
most two. Two is a comparison; three is a catalogue.

Scope
-----

:data:`SUBSTRATE_NAME_EXEMPT_PACKAGES` has exactly two entries and each is
stated rather than left to a path accident, on the precedent
``tools/lints/__main__.py`` sets with ``RULE_TREE_SCOPE``:

* the adapter package itself — the adapters' own home, where a substrate name
  is the module's whole subject;
* the similarity package — a *different* pluggable axis with its own Protocol,
  whose reference vector index shares a stem with one graph adapter. The token
  there names an index, not a graph substrate, and the rule has no business
  reading it as one.

The backend registry is deliberately **not** exempt. It derives its adapter set
and names none of them, so it needs no allowance — and proving that with a
passing rule is stronger evidence for property (2) than an exemption would be.

No allowlist (D-13)
-------------------

No rule here takes an allowlist. Carve-outs are module-path constants in this
file, reviewed with the code, never a data file or per-module opt-out — a data
allowlist would void the invariant it exists to enforce.

What this checker cannot see
----------------------------

Listed here rather than discovered later, because the standing lesson of Phase
15.1 is that a check which does not say what it is blind to is how a defect
class survives five reviews.

* **A name that is never spelled in one piece.** Assembled at runtime from
  fragments, held in a variable, or read from a file. The matcher reads AST
  nodes, not values.
* **A dynamic import of an adapter module.** ``importlib.import_module`` is
  invisible here for the same reason it is invisible to
  ``cinv02-backend-import``; that rule's docstring carries the residual and
  names the compensating control.
* **Behavioural coupling without naming.** A core module that depends on one
  adapter's quirks while naming none of them is beyond any lexical rule. That
  one belongs to review.
* **``#`` comments.** Not AST nodes. Neither sub-rule reads them.
* **Prose under ``docs/`` and ``public/``.** Outside the linted trees
  entirely — this checker sees Python modules in the trees
  ``tools/lints/__main__.py`` scopes it to, and nothing else.
"""

from __future__ import annotations

import ast
import pathlib
import re

from tools.lints import format_finding, matches_module, read_tree

RULE_SUBSTRATE_NAME = "cinv04-substrate-name"
RULE_SUBSTRATE_PROSE = "cinv04-substrate-prose"

#: Path parts, relative to the repo root, of the adapter package the vocabulary
#: is read from. A path rather than a dotted name because this is a disk read,
#: not an import — nothing here imports an adapter.
BACKENDS_DIR_PARTS: tuple[str, ...] = ("src", "ccf", "graph", "backends")

#: Stripped from a stem before it enters the vocabulary, so a write module and
#: its read module contribute one name rather than two. Kept in step with
#: ``tools.lints.harness_imports.WRITE_MODULE_SUFFIX`` by D-01, which gives both
#: files the same convention to read.
WRITE_MODULE_SUFFIX = "_write"

#: The stem never treated as an adapter name.
PACKAGE_INIT_STEM = "__init__"

#: Distinct substrate names in one docstring that make it an enumeration rather
#: than a comparison. Measured: legitimate comparative prose in core names at
#: most two.
PROSE_DISTINCT_THRESHOLD = 3

#: Packages where a substrate name is legitimate. Two entries, each argued in
#: the module docstring. The backend registry is deliberately absent.
SUBSTRATE_NAME_EXEMPT_PACKAGES: frozenset[str] = frozenset(
    {"ccf.graph.backends", "ccf.similarity"}
)

#: Word-boundary matcher, built per vocabulary word. ``_`` is a boundary here on
#: purpose — see the module docstring.
_WORD_PATTERN = r"(?i)(?<![a-z0-9]){word}(?![a-z0-9])"

#: Derived vocabularies and their compiled matchers, cached per base so one
#: ``--all`` run stats the adapter directory once instead of once per file.
#: The cache is keyed by the base it was read from; a caller that mutates the
#: adapter directory between calls with the same base gets the first reading.
_VOCABULARY_CACHE: dict[pathlib.Path, frozenset[str]] = {}
_MATCHER_CACHE: dict[pathlib.Path, tuple[tuple[str, re.Pattern[str]], ...]] = {}


def substrate_vocabulary(base: pathlib.Path) -> frozenset[str]:
    """Substrate names, read from the adapter package under `base`.

    The stem of every ``*.py`` file in :data:`BACKENDS_DIR_PARTS`, less
    :data:`PACKAGE_INIT_STEM` and less a trailing :data:`WRITE_MODULE_SUFFIX`.
    A base with no adapter package yields the empty set, which makes both rules
    silent rather than wrong.
    """
    cached = _VOCABULARY_CACHE.get(base)
    if cached is not None:
        return cached

    stems: set[str] = set()
    for module_path in sorted(base.joinpath(*BACKENDS_DIR_PARTS).glob("*.py")):
        stem = module_path.stem
        if stem == PACKAGE_INIT_STEM:
            continue
        if stem.endswith(WRITE_MODULE_SUFFIX):
            stem = stem[: -len(WRITE_MODULE_SUFFIX)]
        if stem:
            stems.add(stem)

    vocabulary = frozenset(stems)
    _VOCABULARY_CACHE[base] = vocabulary
    return vocabulary


def _matchers(base: pathlib.Path) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """(name, compiled matcher) for every word in the vocabulary under `base`."""
    cached = _MATCHER_CACHE.get(base)
    if cached is not None:
        return cached

    matchers = tuple(
        (word, re.compile(_WORD_PATTERN.format(word=re.escape(word))))
        for word in sorted(substrate_vocabulary(base))
    )
    _MATCHER_CACHE[base] = matchers
    return matchers


def repo_base_for(path: pathlib.Path) -> pathlib.Path:
    """Nearest ancestor of `path` that holds the adapter package.

    The shared per-file checker contract is ``(path, module_name)`` with no base,
    so the base is recovered from the path being checked. Falls back to the
    working directory, which is where ``python -m tools.lints`` runs from.
    """
    for candidate in path.parents:
        if candidate.joinpath(*BACKENDS_DIR_PARTS).is_dir():
            return candidate
    return pathlib.Path.cwd()


def _docstring_positions(tree: ast.Module) -> tuple[set[int], list[ast.Constant]]:
    """The docstring Constant nodes, by ``id()`` and in source order.

    A docstring is the first statement of a module, class or function body when
    that statement is a string constant — a structural test, never a textual
    one.
    """
    by_id: set[int] = set()
    nodes: list[ast.Constant] = []
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
            constant = body[0].value
            if id(constant) not in by_id:
                by_id.add(id(constant))
                nodes.append(constant)
    nodes.sort(key=lambda n: (n.lineno, n.col_offset))
    return by_id, nodes


def _code_texts(node: ast.AST, docstring_ids: set[int]) -> list[str]:
    """Text a node contributes to sub-rule 2a, if any."""
    if isinstance(node, ast.Constant):
        if id(node) in docstring_ids or not isinstance(node.value, str):
            return []
        return [node.value]
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.arg):
        return [node.arg]
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, ast.alias):
        return [part for part in (node.name, node.asname) if part]
    return []


def _hits(
    text: str, matchers: tuple[tuple[str, re.Pattern[str]], ...]
) -> list[str]:
    """Distinct vocabulary words `text` contains, in vocabulary order."""
    return [word for word, pattern in matchers if pattern.search(text)]


def check_source(
    source: str,
    path: pathlib.Path,
    module_name: str,
    base: pathlib.Path | None = None,
) -> list[str]:
    """Check already-read `source` attributed to `path` / `module_name`."""
    if matches_module(module_name, SUBSTRATE_NAME_EXEMPT_PACKAGES):
        return []

    matchers = _matchers(base if base is not None else repo_base_for(path))
    if not matchers:
        return []

    tree = read_tree(source, path)
    docstring_ids, docstrings = _docstring_positions(tree)
    found: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        for text in _code_texts(node, docstring_ids):
            hits = _hits(text, matchers)
            if not hits:
                continue
            found.append(
                (
                    getattr(node, "lineno", 0),
                    RULE_SUBSTRATE_NAME,
                    f"{module_name!r} names the graph substrate"
                    f" {', '.join(hits)} in a code position. Core resolves the"
                    " adapter a deployment names through the registry and"
                    " names none of them itself (D-IMPL-93 property (2)). The"
                    " vocabulary this rule reads is derived from the adapter"
                    " package on disk, so it needs no edit when the set of"
                    " adapters changes.",
                )
            )

    for docstring in docstrings:
        hits = _hits(docstring.value, matchers)
        if len(hits) < PROSE_DISTINCT_THRESHOLD:
            continue
        found.append(
            (
                docstring.lineno,
                RULE_SUBSTRATE_PROSE,
                f"one docstring in {module_name!r} enumerates {len(hits)}"
                f" substrates ({', '.join(hits)}). At"
                f" {PROSE_DISTINCT_THRESHOLD} or more this is per-adapter"
                " prose: correct only until the next adapter, and edited once"
                " per adapter forever. Describe the seam, not the list. Two"
                " names is a comparison and stays legal; three is a"
                " catalogue.",
            )
        )

    found.sort(key=lambda item: (item[0], item[1]))
    return [
        format_finding(path, lineno, rule, message) for lineno, rule, message in found
    ]


def check(
    path: pathlib.Path, module_name: str, base: pathlib.Path | None = None
) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(
        path.read_text(encoding="utf-8"), path, module_name, base=base
    )
