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

**And it refuses when it cannot read one.** A derived vocabulary has a failure
mode a typed list does not: the derivation can come back empty, and an empty
vocabulary passes every file while guarding nothing. That is fail-open, so it
raises :class:`EmptySubstrateVocabulary` instead (review finding WR-03).

Two things the derivation cannot decide for itself
--------------------------------------------------

The vocabulary's *blast radius* is set by adapter module naming, and nothing in
that naming is chosen with this rule in mind. A stem whose spelling collides
with vocabulary core legitimately uses for something else would make every use
of that word a violation across ``src/`` — with no edit here and no warning.

:data:`GENERIC_WORD_STEMS` is the stated escape (review finding WR-04): a stem
listed there is matched as a whole token rather than under the loose boundary
below, so ``"in-memory"`` and ``memory_budget`` in an unrelated module are not
read as "core names the graph substrate", while a bare adapter name still is.
It is a named constant reviewed with the code (D-13), it narrows how a word
matches rather than exempting any module from the rule, and its cost is stated
at the constant.

Sub-rule 2a — code positions
----------------------------

Matching is by the word-boundary pattern ``(?i)(?<![a-z0-9])<name>(?![a-z0-9])``.
The boundary is deliberately loose: it treats ``_`` as a boundary character, so
``<name>_dsn`` and ``<name>_uri`` match. Tightening it *everywhere* was measured
and rejected — it stops the rule catching a reintroduced ``<name>_dsn``
parameter, which is the exact thing the rule exists to catch.

The tight pattern is applied to :data:`GENERIC_WORD_STEMS` and nowhere else, so
the trade is paid once per colliding word rather than across the whole
vocabulary. Everything about that trade — what it buys, what it gives up, and
when to add an entry — is stated at the constant.

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

#: The strict matcher, for the stems in :data:`GENERIC_WORD_STEMS`. ``_`` and
#: ``-`` are *not* boundaries here, so the stem matches only as a whole token.
_STRICT_WORD_PATTERN = r"(?i)(?<![a-z0-9_-]){word}(?![a-z0-9_-])"

#: Adapter stems that are also ordinary English, matched strictly rather than
#: loosely (review finding WR-04). Named constants reviewed with the code, per
#: D-13 — not an allowlist, and not a per-module opt-out: this narrows *how* a
#: word matches everywhere, it does not exempt anybody from the rule.
#:
#: **Why the escape exists.** The vocabulary is derived from adapter module
#: names, and nothing bounds what those names are. One of today's adapters is
#: named for a word core uses about something else entirely, so under the loose
#: boundary a cache mode spelled ``"in-memory"`` and a parameter named
#: ``memory_budget`` in an unrelated module both read as "core names the graph
#: substrate" — neither line being about a graph substrate at all. The rule
#: passes today only because no such literal happens to exist outside the two
#: exempt packages, which is luck rather than design.
#:
#: **What it costs, stated rather than discovered.** For a stem listed here the
#: rule no longer catches ``<stem>_dsn``, ``<stem>_uri`` or ``open_<stem>`` —
#: the compound forms the loose boundary exists to catch. It still catches the
#: form that actually matters and the one every deletion in this phase took:
#: the bare adapter name as a literal, a parameter, or a ``def``. A stem is
#: added here only when its spelling collides with vocabulary core legitimately
#: uses for something else, and adding one is a reviewed code change — which is
#: the trade D-13 asks for over a data file nobody reads.
#:
#: **Not a substrate list.** Every entry is a *word*, and a stem here that no
#: adapter is named after simply never enters the vocabulary and does nothing.
GENERIC_WORD_STEMS: frozenset[str] = frozenset({"memory"})

#: Derived vocabularies and their compiled matchers, cached per base so one
#: ``--all`` run stats the adapter directory once instead of once per file.
#: The cache is keyed by the base it was read from; a caller that mutates the
#: adapter directory between calls with the same base gets the first reading.
_VOCABULARY_CACHE: dict[pathlib.Path, frozenset[str]] = {}
_MATCHER_CACHE: dict[pathlib.Path, tuple[tuple[str, re.Pattern[str]], ...]] = {}


class EmptySubstrateVocabulary(RuntimeError):
    """The rule could not read the vocabulary it enforces against.

    Its own type so a caller can tell "this checker cannot see its subject"
    apart from "this file is fine" — which is the distinction the empty set
    erased (review finding WR-03).
    """


def substrate_vocabulary(base: pathlib.Path) -> frozenset[str]:
    """Substrate names, read from the adapter package under `base`.

    The stem of every ``*.py`` file in :data:`BACKENDS_DIR_PARTS`, less
    :data:`PACKAGE_INIT_STEM` and less a trailing :data:`WRITE_MODULE_SUFFIX`.

    **Refuses rather than returning an empty set** (review finding WR-03). It
    used to answer with the empty set when the adapter package was missing or
    held no adapters, and :func:`check_source` then returned no findings for
    every file — which the docstring called "silent rather than wrong". It is
    silent rather than *safe*: a rule with an empty vocabulary passes every
    file while guarding nothing, and that is the same defect class this
    module's own docstring indicts three paragraphs earlier — "a rule pinned to
    one file stops enforcing anything the moment that file splits, and it stops
    *silently*".

    The trigger is not hypothetical. :data:`BACKENDS_DIR_PARTS` is a path this
    file states and the adapter package's location is not this file's to
    decide; :func:`repo_base_for` falls back to the working directory when no
    ancestor holds the package, so a run from the wrong directory reached the
    empty set by an ordinary route.

    Raises:
        EmptySubstrateVocabulary: the adapter package is not a readable
            directory under `base`, or holds no adapter modules.
    """
    cached = _VOCABULARY_CACHE.get(base)
    if cached is not None:
        return cached

    directory = base.joinpath(*BACKENDS_DIR_PARTS)
    if not directory.is_dir():
        raise EmptySubstrateVocabulary(
            f"{RULE_SUBSTRATE_NAME} derives its vocabulary from {directory},"
            " which is not a readable directory. A rule with an empty"
            " vocabulary passes every file while guarding nothing, so it"
            " refuses instead. Either the run is rooted somewhere other than"
            " the repository, or the adapter package moved and"
            " BACKENDS_DIR_PARTS needs updating."
        )

    stems: set[str] = set()
    for module_path in sorted(directory.glob("*.py")):
        stem = module_path.stem
        if stem == PACKAGE_INIT_STEM:
            continue
        if stem.endswith(WRITE_MODULE_SUFFIX):
            stem = stem[: -len(WRITE_MODULE_SUFFIX)]
        if stem:
            stems.add(stem)

    if not stems:
        raise EmptySubstrateVocabulary(
            f"{RULE_SUBSTRATE_NAME} read {directory} and found no adapter"
            " modules, so it has nothing to enforce against. An adapter"
            " package with no adapters in it is a broken checkout or a moved"
            " package, not a deployment with no substrates — the SDK ships"
            " its own."
        )

    vocabulary = frozenset(stems)
    _VOCABULARY_CACHE[base] = vocabulary
    return vocabulary


def _matchers(base: pathlib.Path) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """(name, compiled matcher) for every word in the vocabulary under `base`."""
    cached = _MATCHER_CACHE.get(base)
    if cached is not None:
        return cached

    matchers = tuple(
        (
            word,
            re.compile(
                (
                    _STRICT_WORD_PATTERN
                    if word in GENERIC_WORD_STEMS
                    else _WORD_PATTERN
                ).format(word=re.escape(word))
            ),
        )
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

    # No empty-matcher escape: `substrate_vocabulary` refuses rather than
    # answering with nothing, so there is no state in which this function
    # returns "clean" because it could not see its own subject (WR-03).
    matchers = _matchers(base if base is not None else repo_base_for(path))

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
