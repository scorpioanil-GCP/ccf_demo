"""CINV-06 — every sentinel-defaulted ``CCFContract`` field declares its hash posture.

``D-IMPL-243`` amendment 1 (Dave: *"Lint: every new sentinel-defaulted field
on a ``CCFContract`` must declare the key. Pre-243 fifteen allowlisted by name
in that lint (not a count). A forgotten key is red, not a quiet upgrade."*);
whitepaper §7.10; CLAUDE.md §7.4. SDK-defined enforcement, not
whitepaper-derived.

**REGISTRATION STATUS: written, tested, and NOT yet registered under
``python -m tools.lints --all``.** Its first run over ``src/`` and ``runtime/``
with the fifteen allowlisted found further pre-243 sentinel-defaulted fields
without the key — the roster is pinned by
``tools/lints/tests/test_hash_transparent_key.py`` and reported in
``24.5-FIX-01-SUMMARY.md`` — and amendment 1 says the allowlist is the
fifteen *and nothing else*. Widening it, or narrowing the rule's universe,
is a ruling, not an executor's call. Until that ruling this module is a
measurement instrument that ``make lint`` does not run; the docstring of
``tools/lints/__init__.py`` says the same, so nothing in the tree implies a
gate that is not standing.

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
by ``Class.field``, unless the field is on the allowlist below.

``cinv06-hash-transparent-key``
    ``Class.field`` declares a default and no ``ccf_hash_transparent`` key —
    or a key whose value is not the literal ``True``/``False``, or a
    ``json_schema_extra`` this checker cannot read statically. All three are
    the same finding: the field's hash posture is not declared where the
    canonicalizer reads it.

Scope: ``src/`` and ``runtime/`` — every tree the canonicalizer's models live
in. Tests and examples declare scratch models by design and are out of scope.

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

The allowlist
-------------
:data:`ALLOWLISTED_PRE_243_FIELDS` — the fifteen fields amendment 1 names, by
``Class.field``, each the pre-243 ``D-IMPL-89`` lineage on the decision
record. A roster, not a count; asserted by test against the amendment's own
measurement (``tests/replay/test_generation_mismatch.py::THE_FIFTEEN``). No
data file: like every other CINV rule but the first, this one takes no
``allowlist.yaml`` entry (``D-13``).
"""

from __future__ import annotations

import ast
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

#: The fifteen (``D-IMPL-243`` amendment 1), model-qualified, and nothing else.
#: ``ContextFabricSnapshot``, ``PolicyBindingsSnapshot``, ``ModelVersionRecord``
#: and ``ContentGenerationPath`` are the four dimension models of
#: ``ccf.replay.record`` the amendment's dotted names resolve to.
ALLOWLISTED_PRE_243_FIELDS: frozenset[str] = frozenset(
    {
        "ContextFabricSnapshot.source_attestation",
        "PolicyBindingsSnapshot.hitl_actions",
        "PolicyBindingsSnapshot.survivor_cap",
        "PolicyBindingsSnapshot.graph_adapter",
        "PolicyBindingsSnapshot.graph_adapter_version",
        "PolicyBindingsSnapshot.graph_secret_refs",
        "ModelVersionRecord.harness_trace",
        "ContentGenerationPath.workflow_step_sequence",
        "ContentGenerationPath.assembly_refusal",
        "ContentGenerationPath.graph_query_sequence",
        "ContentGenerationPath.debt",
        "ContentGenerationPath.debt_evidence",
        "ContentGenerationPath.source_refresh_recency",
        "ContentGenerationPath.obligation_in_force",
        "ContentGenerationPath.request",
    }
)

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


def check_tree(base: pathlib.Path) -> list[str]:
    """Report every defaulted contract field whose hash posture is undeclared."""
    findings: list[str] = []
    for field in defaulted_fields(base):
        if field.qualified in ALLOWLISTED_PRE_243_FIELDS:
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
                f"{field.qualified} {detail} (D-IMPL-243 amendment 1)",
            )
        )
    return findings
