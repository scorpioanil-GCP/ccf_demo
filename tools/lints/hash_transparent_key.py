"""CINV-06 — every sentinel-defaulted ``CCFContract`` field NEW since ``13bd250`` declares its hash posture.

``D-IMPL-243`` amendment 1 (Dave: *"Lint: every new sentinel-defaulted field
on a ``CCFContract`` must declare the key. … A forgotten key is red, not a
quiet upgrade."*) and amendment 2 (Dave: *"New-since-13bd250 only. Do not
allowlist 115 names. Lint: field absent at 13bd250 → must declare
``ccf_hash_transparent``. Older fields are D-IMPL-89 by construction. The
fifteen stay a named roster on the replay check only (record shape), not a
second copy of the lint universe. Base roster is a committed file measured at
``13bd250``, not a comment."*); whitepaper §7.10; CLAUDE.md §7.4.
SDK-defined enforcement, not whitepaper-derived. Registered under
``python -m tools.lints --all`` (``make lint``) as ``hash-transparent-key``.

The rule
--------
A field on a ``CCFContract`` subclass that has a default — a plain ``= value``,
or ``Field(default=…)`` / ``Field(default_factory=…)`` / a positional default
— renders into every content hash of every instance unless it is marked
``ccf_hash_transparent: True`` (omitted at its sentinel), and a stored object
lacking it is either a generation boundary (``False``) or the ``D-IMPL-89``
lineage (no key). The three states mean three different things at
``replay()``, so the state must be **declared**, in the field's
``json_schema_extra``, as the literal ``True`` or the literal ``False``.
This checker reports every defaulted field whose declaration does neither,
by ``Class.field`` — **unless the field is in the base roster.**

``cinv06-hash-transparent-key``
    ``Class.field`` declares a default, is not in the base roster, and
    declares no ``ccf_hash_transparent`` key — or a key whose value is not
    the literal ``True``/``False``, or a ``json_schema_extra`` this checker
    cannot read statically. All three are the same finding: the field's hash
    posture is not declared where the canonicalizer reads it.

Scope: ``src/`` and ``runtime/`` — every tree the canonicalizer's models live
in. Tests and examples declare scratch models by design and are out of scope.

The universe: new since ``13bd250``, measured
--------------------------------------------
The lint's universe is the defaulted contract fields that did NOT exist with
a default in the Phase 24.5 base tree. The boundary is a committed file,
``tools/lints/hash_transparent_base_roster.json`` — every defaulted
``CCFContract`` field at ``13bd250``, ``module.Class.field``, 130 names —
generated from ``git archive 13bd250`` by ``tools/lints/base_roster.py``
with the same :func:`defaulted_fields` walker this checker runs over HEAD,
and held equal to a fresh measurement by that module's ``--check`` (and by
``tools/lints/tests/test_base_roster.py``). A field in the roster is silent
here whatever it declares: it predates the mark, its default has rendered
into every hash since it shipped, and a stored object lacking it is the
``D-IMPL-89`` compatibility case — the lineage amendment 2 calls "by
construction". The fifteen fields amendment 1 named on the decision record
are in the roster like any other pre-phase field; **they are no longer a
list in this module.** As a roster they live on the replay check —
``tests/replay/test_generation_mismatch.py::THE_FIFTEEN`` — which is about the
record's shape, not about the lint's universe.

Why a roster and not an allowlist, in Dave's words: *"Not 2 — 130-name roster
will rot. Not 3 — 'hashed family' is another judgment the lint cannot see."*
The roster does not rot because nothing is ever added to it by hand: it is a
measurement of one immutable tree, and ``--check`` proves the file is that
measurement. A field added after the base is in the universe forever, and
declares the key or is red.

What "a ``CCFContract`` subclass" means to an AST
-------------------------------------------------
Subclassing crosses files, so this is a **whole-tree** checker in the shape
of ``citations``: every ``class`` under the scope trees is collected first,
and the closure of bases named ``CCFContract`` — by simple name, through any
depth of intermediate classes — is the universe. Matching by simple name
over-includes a same-named unrelated class (the safe direction for a lint)
and misses a base reached only through an alias; the compensating control is
``test_the_ast_universe_equals_the_imported_universe`` in this checker's
test module, which imports every model and holds the two rosters equal.

No allowlist. Like every other CINV rule but the first, this one takes no
``allowlist.yaml`` entry (``D-13``), and it carries no name list of its own.
"""

from __future__ import annotations

import ast
import json
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass

from tools.lints import format_finding

RULE_HASH_TRANSPARENT_KEY = "cinv06-hash-transparent-key"

#: The key, spelled here rather than imported: a lint that imported the SDK to
#: learn the key's name would be running the code it lints.
KEY_NAME = "ccf_hash_transparent"
KEY_SYMBOL = "HASH_TRANSPARENT_KEY"

#: The root of the universe, by simple name.
CONTRACT_BASE = "CCFContract"

#: Trees this checker walks. ``tests`` and ``examples`` are out of scope by
#: design — they declare scratch models — and the archive is not core.
SCOPE_TREES: tuple[str, ...] = ("src", "runtime")

#: The committed base roster (``D-IMPL-243`` amendment 2): generated and
#: checked by ``tools/lints/base_roster.py``, read here with the stdlib. The
#: header keys are asserted by that module's ``load``; this reader takes only
#: the names, because a lint that refused to run on a malformed roster would
#: be red for the wrong reason — ``test_base_roster.py`` is where the file's
#: shape is held.
BASE_ROSTER_PATH = pathlib.Path(__file__).with_name("hash_transparent_base_roster.json")

SKIP_DIRS: frozenset[str] = frozenset(
    {"__pycache__", ".git", ".venv", "venv", "build", "dist", ".mypy_cache"}
)


@dataclass(frozen=True)
class _ClassSite:
    path: pathlib.Path
    node: ast.ClassDef
    bases: tuple[str, ...]


@dataclass(frozen=True)
class DefaultedField:
    """One defaulted field on a contract, with what its declaration says."""

    path: pathlib.Path
    lineno: int
    class_name: str
    field_name: str
    #: ``True`` / ``False`` when declared as a literal; ``None`` when the key is
    #: absent; the string ``"unreadable"`` when ``json_schema_extra`` is not a
    #: dict literal this checker can read, or the key's value is not a literal
    #: boolean.
    declared: bool | None | str

    @property
    def qualified(self) -> str:
        return f"{self.class_name}.{self.field_name}"


def module_qualified(field: DefaultedField, base: pathlib.Path) -> str:
    """``module.Class.field`` for ``field``, the base roster's spelling.

    The module is derived from the field's path relative to the scope tree
    that holds it — ``src/ccf/replay/record.py`` is ``ccf.replay.record``,
    ``runtime/ccf_runtime/cdc/envelope_map.py`` is ``ccf_runtime.cdc.envelope_map``
    — the same derivation ``tools/lints/__main__.py::module_name_for`` uses
    for every per-file rule. Module-qualified rather than ``Class.field``
    because the roster is a claim about a commit, and a same-named class in
    another module is a different declaration.
    """
    path = field.path.resolve()
    for tree in SCOPE_TREES:
        root = (base / tree).resolve()
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join([*parts, field.class_name, field.field_name])
    raise ValueError(f"{field.path} is under none of {SCOPE_TREES} in {base}")


def base_roster(path: pathlib.Path = BASE_ROSTER_PATH) -> frozenset[str]:
    """The names in the committed base roster — the fields OUTSIDE the universe."""
    document = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(document["fields"])


def _base_name(expr: ast.expr) -> str | None:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    if isinstance(expr, ast.Subscript):
        # ``Generic[T]``-style bases carry no contract; ``Base[X]`` is rare
        # and reads as its value's name.
        return _base_name(expr.value)
    return None


def _iter_python_files(root: pathlib.Path) -> Iterator[pathlib.Path]:
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def _collect_classes(base: pathlib.Path) -> list[_ClassSite]:
    sites: list[_ClassSite] = []
    for tree in SCOPE_TREES:
        root = base / tree
        if not root.is_dir():
            continue
        for path in _iter_python_files(root):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(module):
                if isinstance(node, ast.ClassDef):
                    bases = tuple(
                        name for name in (_base_name(b) for b in node.bases) if name
                    )
                    sites.append(_ClassSite(path=path, node=node, bases=bases))
    return sites


def contract_classes(base: pathlib.Path) -> list[_ClassSite]:
    """Every class under the scope trees that descends from ``CCFContract`` by name."""
    sites = _collect_classes(base)
    contracts: set[str] = {CONTRACT_BASE}
    changed = True
    while changed:
        changed = False
        for site in sites:
            if site.node.name in contracts:
                continue
            if any(b in contracts for b in site.bases):
                contracts.add(site.node.name)
                changed = True
    return [s for s in sites if s.node.name in contracts and s.node.name != CONTRACT_BASE]


def _is_classvar(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Subscript):
        return _base_name(annotation.value) == "ClassVar"
    return _base_name(annotation) == "ClassVar"


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _is_key(expr: ast.expr | None) -> bool:
    if isinstance(expr, ast.Constant):
        return expr.value == KEY_NAME
    return _base_name(expr) == KEY_SYMBOL if expr is not None else False


def _read_declaration(value: ast.expr) -> tuple[bool, bool | None | str]:
    """``(has_default, declared)`` for one field's assigned value."""
    if not (isinstance(value, ast.Call) and _base_name(value.func) == "Field"):
        # ``x: T = anything-else`` — a plain default, no ``json_schema_extra``.
        return True, None
    has_default = bool(value.args) or any(
        kw.arg in ("default", "default_factory") for kw in value.keywords
    )
    extra = _keyword(value, "json_schema_extra")
    if extra is None:
        return has_default, None
    if not isinstance(extra, ast.Dict):
        return has_default, "unreadable"
    for key, item in zip(extra.keys, extra.values, strict=True):
        if _is_key(key):
            if isinstance(item, ast.Constant) and isinstance(item.value, bool):
                return has_default, item.value
            return has_default, "unreadable"
    return has_default, None


def defaulted_fields(base: pathlib.Path) -> list[DefaultedField]:
    """Every defaulted field on every contract class, with its declared state."""
    found: list[DefaultedField] = []
    for site in contract_classes(base):
        for stmt in site.node.body:
            if not isinstance(stmt, ast.AnnAssign) or stmt.value is None:
                continue
            if not isinstance(stmt.target, ast.Name):
                continue
            name = stmt.target.id
            if name.startswith("_") or _is_classvar(stmt.annotation):
                continue
            has_default, declared = _read_declaration(stmt.value)
            if not has_default:
                continue
            found.append(
                DefaultedField(
                    path=site.path,
                    lineno=stmt.lineno,
                    class_name=site.node.name,
                    field_name=name,
                    declared=declared,
                )
            )
    return found


def check_tree(base: pathlib.Path, roster: frozenset[str] | None = None) -> list[str]:
    """Report every defaulted contract field outside the base roster whose hash posture is undeclared.

    ``roster`` defaults to the committed base roster; a test that pins a
    scratch roster passes its own. The membership test is module-qualified,
    so a scratch tree's ``scratch.m.Planted.forgotten`` is in the universe
    however its class is named.
    """
    outside = base_roster() if roster is None else roster
    findings: list[str] = []
    for field in defaulted_fields(base):
        if module_qualified(field, base) in outside:
            continue
        if field.declared is True or field.declared is False:
            continue
        if field.declared == "unreadable":
            detail = (
                f"declares a default and a {KEY_NAME!r} this checker cannot read"
                " statically — the key must be the literal True or False inside a"
                " dict literal json_schema_extra"
            )
        else:
            detail = (
                f"declares a default and no {KEY_NAME!r} key — declare True (omitted"
                " at its sentinel: silence equals yesterday) or False (a generation"
                " boundary: refused by name at replay); a forgotten key is red, not"
                " a quiet upgrade"
            )
        findings.append(
            format_finding(
                field.path,
                field.lineno,
                RULE_HASH_TRANSPARENT_KEY,
                f"{field.qualified} {detail} (D-IMPL-243 amendments 1 and 2)",
            )
        )
    return findings
