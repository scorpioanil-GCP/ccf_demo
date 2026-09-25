"""D-IMPL-353 §4 — authorization as a capability: the ``None``-default lint.

SDK-defined (CLAUDE.md §7.3, §8.2, §11 — the authorization plane is an
extension beyond the whitepaper). The one lint that stays beside
``mypy --strict`` once :class:`~ccf_runtime.authz.capability.Authorized` is the
mechanism, narrowed to what a type checker cannot see: a capability parameter
that is *allowed to be absent*. ``authorizer: TenantAuthorizerProtocol | None
= None`` **is** ``D-IMPL-73``, and it is the shape behind P4 and behind the
original finding — an authorization seam that is optional by construction is
one that every caller may decline, and the served surface behind it runs
unauthorized with every test green.

Six rules, one AST walk, ``src/`` and ``runtime/`` (``RULE_TREE_SCOPE``):

``d353-authz-default``  (rule 1 — THE rule)
    A parameter — of a function, method, lambda, or a class-body field, which
    is a dataclass's or model's generated parameter — that is *authority-typed*
    and carries ANY default, ``None`` or otherwise. Authority-typed means the
    annotation's union members include one of :data:`AUTHORITY_TYPES` (by
    head name, through import aliases, qualified spellings and quoted forward
    references), OR the parameter is *named* for authority
    (:data:`AUTHORITY_PARAM_NAMES`) — the second arm because an unannotated
    ``authorizer=None`` is the same defect with the type removed.

``d353-authz-weak-type``  (rule 2)
    An authority parameter whose type admits absence or anything: a union
    with ``None`` (``X | None``, ``Optional[X]``, ``Union[X, None]``),
    ``object``, ``Any``, no annotation at all, or a kind-less capability —
    bare ``Authorized``, ``Authorized[Any]``, ``Authorized[ActionKind]`` — which
    under D-IMPL-353 §1.5(b) is a wand rather than a proof. ``verify`` in the
    capability module takes ``authorized: object`` *by design* (§1.5c — "a
    handle must not trust its annotation"), so the ``object``/``Any`` arm is
    exempt in :data:`CAPABILITY_MODULE` — the definer, not the shim — and
    nowhere else. The other arms apply there too.

``d353-authz-mint-site``  (rule 3)
    A third producer. The capability is DEFINED once, in
    :data:`CAPABILITY_MODULE` (``src/ccf/authz/capability.py`` — D-29 moved it
    into ``src/`` so library handles can require it without importing
    ``runtime/``); :data:`CAPABILITY_SHIM` (``ccf_runtime.authz.capability``)
    re-exports every public name and defines nothing. Outside the definer:
    any construction of ``Authorized(...)`` in any spelling; any reference to
    the module-private sentinel ``_SENTINEL`` — as a name, an attribute, an
    import, or the string ``"_SENTINEL"`` (which is what ``getattr(capability,
    "_SENTINEL")`` looks like). And two call rules, each resolved through the
    import so that ``mint`` reached through the shim is the same symbol as
    ``mint`` reached from the definer (:data:`CAPABILITY_SPELLINGS`): a call to
    ``mint`` from any module not in :data:`MINT_SITES` — §1.1 commits to
    *exactly two mint sites*, the HTTP gate and the MCP wrapper — and a call
    to ``mint_at_composition`` from any module not in
    :data:`COMPOSITION_MINT_SITES` — §2 P3: ``ReplayMint`` is "handed to the
    fabric's replay writer at composition by the deployment", made once at
    boot by the composition root, which in this codebase is ``ccf.boot``
    (``harness_imports.py`` names it so for single-writer). **The shim is in
    neither site set**: an allowed importer is not an allowed minter, and a
    rule keyed on the runtime path would pass a call that reaches the real
    mint through it. A ``mint`` method on some other object is not this
    rule's subject.

``d353-authz-raw-registration``  (rule 4)
    An MCP surface registered on anything but the ``TenantGuardedServer``
    wrapper. Outside :data:`TENANT_GUARD_MODULE`, a call or decorator
    ``<receiver>.tool(...)`` / ``.resource(...)`` / ``.add_tool(...)`` /
    ``.add_resource(...)`` is permitted only when the receiver is **provably
    the wrapper**: a bare name whose EVERY binding in the module is a
    ``TenantGuardedServer(...)`` construction or a ``TenantGuardedServer``
    annotation, or the construction itself. Any other receiver — a
    ``FastMCP``, ``self._server``, ``door.fastmcp``, a name bound to the
    wrapper in one function and to a raw server in another — is refused.
    Default-deny: an unprovable receiver is reported, never guessed at.
    A raw-registered body has no ``authorized`` to hand any handle (§2 P9).

``d353-authz-unguarded-route``  (rule 5)
    In :data:`ROUTES_PACKAGE` only: a handler decorated with a route verb
    (``@<anything>.get(...)``, ``.post``, …, ``.api_route``) and not also with
    ``@authorizes(...)``; and any programmatic ``add_api_route`` registration,
    whose declaration cannot be read statically. The static twin of the
    gate's boot-time ``UndeclaredRouteError`` (SEC-001): the gate refuses to
    build an application with an undeclared route; this refuses the commit.

``d353-authz-type-ignore``  (rule 6)
    The static tooth overridden. §1.5(b) is the claim that a wrong-kind or
    absent capability *does not type-check*; §4 opens by naming the one thing
    that defeats it — "a call site passing ``None  # type: ignore``" — and
    §1.5(b) says this lint refuses it. A ``# type: ignore`` comment (a real
    comment token, never a docstring) is refused when its line lies inside a
    call that passes an authority keyword (:data:`AUTHORITY_PARAM_NAMES`) or a
    ``*``/``**`` splat — whose contents the type checker cannot see, so the
    ignore is the only thing standing between an untyped bag and a required
    seam — inside an assignment annotated with an authority type, or on the
    signature line of a function that takes an authority parameter. Any
    error code; the code names what was overridden, not whether it was. An
    ignore with no authority in reach (``model_fields  # type:
    ignore[attr-defined]``) is not this rule's subject. Measured at the seam:
    one finding, ``ccf_runtime.cli.main`` splatting ``**authority`` — typed
    ``Mapping[str, object] | None = None`` — into ``create_app``.

No rule here takes an allowlist. Carve-outs are the module-path constants
below, reviewed with the code, on the same principle as ``harness_imports.py``
— an authorization invariant with a data-file opt-out is not an invariant.

Fork-point red is the acceptance test (§4). Against ``d895d889`` this lint
reports ``create_app(deps, *, auth: HttpAuthProtocol | None = None,
authorizer: TenantAuthorizerProtocol | None = None, ...)`` at
``runtime/ccf_runtime/http_api/app.py:193-194`` under rules 1 and 2;
``tools/lints/tests/test_authorization_invariant.py`` checks the commit out
and asserts it.

Residuals, stated. Dynamic construction — ``getattr`` with a computed string,
``importlib``, ``globals()`` — is outside every static rule here, exactly as
``D-12`` accepts for ``cinv01c``; the runtime tooth (``verify`` comparing the
mint by identity) is what those meet. ``*args``/``**kwargs`` carry no
per-parameter annotation and are not read. A route registered outside the
routes package meets the gate's boot check instead of rule 5.
"""

from __future__ import annotations

import ast
import io
import pathlib
import re
import tokenize
from dataclasses import dataclass, field
from typing import Callable, Iterator

from tools.lints import format_finding, package_for, read_tree

RULE_DEFAULT = "d353-authz-default"
RULE_WEAK_TYPE = "d353-authz-weak-type"
RULE_MINT_SITE = "d353-authz-mint-site"
RULE_RAW_REGISTRATION = "d353-authz-raw-registration"
RULE_UNGUARDED_ROUTE = "d353-authz-unguarded-route"
RULE_TYPE_IGNORE = "d353-authz-type-ignore"

#: The authority types. A parameter annotated with any of these — bare,
#: subscripted, quoted, aliased, qualified, or as a member of a union — is an
#: authority parameter for rules 1 and 2.
AUTHORITY_TYPES: frozenset[str] = frozenset(
    {
        "Authorized",
        "TenantAuthorizerProtocol",
        "HttpAuthProtocol",
        "TokenVerifier",
        "TokenSourceProtocol",
    }
)

#: Parameter names that are authority parameters whatever their annotation —
#: the arm that sees ``def f(authorizer=None)`` with the type removed, and
#: ``authorized: object``, where no type is left to match on. Exact match; a
#: name that merely begins with one of these is not one of these.
AUTHORITY_PARAM_NAMES: frozenset[str] = frozenset(
    {"auth", "authorizer", "authorized", "token_verifier", "token_source"}
)

#: Annotation heads that admit anything.
WEAK_HEADS: frozenset[str] = frozenset({"object", "Any"})

#: Type arguments that make ``Authorized[...]`` kind-less (§1.5b).
KINDLESS_SLICES: frozenset[str] = frozenset({"Any", "ActionKind"})

#: The module that DEFINES ``Authorized``, its sentinel, ``mint`` and
#: ``mint_at_composition`` — the one owner of the sentinel. Exempt from rule 3
#: and from rule 2's ``object``/``Any`` arm, and from nothing else.
CAPABILITY_MODULE = "ccf.authz.capability"
#: The runtime re-export shim. It re-exports the public names so the gate, the
#: wrapper and the engine keep their import path; it defines nothing and it
#: is deliberately in NEITHER site set below.
CAPABILITY_SHIM = "ccf_runtime.authz.capability"
#: Both spellings resolve to the same symbols: a ``mint`` imported from
#: either is the capability's ``mint``.
CAPABILITY_SPELLINGS: frozenset[str] = frozenset({CAPABILITY_MODULE, CAPABILITY_SHIM})
AUTHORIZED_NAME = "Authorized"
SENTINEL_NAME = "_SENTINEL"
MINT_NAME = "mint"
COMPOSITION_MINT_NAME = "mint_at_composition"
#: The two capability producers rule 3 resolves calls to.
MINT_SYMBOLS: frozenset[str] = frozenset({MINT_NAME, COMPOSITION_MINT_NAME})

#: The modules that may call ``mint`` — §1.1's two producers, plus the module
#: that defines it. A third member here is a third mint site and is reviewed
#: as one. The shim is not a member: an allowed importer is not an allowed
#: minter.
MINT_SITES: frozenset[str] = frozenset(
    {CAPABILITY_MODULE, "ccf_runtime.http_api.gate", "ccf_runtime.mcp.tenancy"}
)

#: The modules that may call ``mint_at_composition`` — the definer and the
#: composition root. ``ReplayMint`` is the one kind no door declares (§2 P3);
#: a gate calling this would hand a served surface the governed-record mint,
#: so the gate modules are deliberately absent. A second root here is a
#: reviewed edit.
COMPOSITION_MINT_SITES: frozenset[str] = frozenset({CAPABILITY_MODULE, "ccf.boot"})

#: The wrapper module and class. Inside the module, registration on the raw
#: server is the wrapper doing its job; everywhere else it is rule 4's subject.
TENANT_GUARD_MODULE = "ccf_runtime.mcp.tenancy"
TENANT_GUARD_CLASS = "TenantGuardedServer"

#: ``FastMCP``'s registration surface, decorator and programmatic forms alike.
REGISTRATION_METHODS: frozenset[str] = frozenset(
    {"tool", "resource", "add_tool", "add_resource"}
)

#: Where HTTP route handlers are defined. Rule 5 reads this package and only
#: this package; ``app.py``'s ``/health`` mount carries its own declaration and
#: meets the gate's boot check.
ROUTES_PACKAGE = "ccf_runtime.http_api.routes"

#: ``APIRouter``'s route decorators. Receiver-agnostic: ``@router.get`` and
#: ``@app.get`` are both routes.
ROUTE_VERBS: frozenset[str] = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "trace", "api_route"}
)
PROGRAMMATIC_ROUTE_METHODS: frozenset[str] = frozenset({"add_api_route"})
AUTHORIZES_NAME = "authorizes"

#: A ``type: ignore`` comment, with or without error codes. Matched against
#: COMMENT tokens only, so a docstring that mentions the phrase is not one.
TYPE_IGNORE_COMMENT = re.compile(r"#\s*type:\s*ignore\b")


# --- module context ------------------------------------------------------------


@dataclass
class _Module:
    """One parsed module and the name resolutions every rule reads."""

    tree: ast.Module
    path: pathlib.Path
    module_name: str
    source: str = ""
    #: local name -> the simple name it was imported as (``Cap`` -> ``Authorized``).
    names: dict[str, str] = field(default_factory=dict)
    #: local name -> the dotted module it may denote (``cap`` -> ``…capability``).
    modules: dict[str, str] = field(default_factory=dict)
    #: local name -> the capability producer it was imported as, for
    #: ``from <either capability spelling> import mint|mint_at_composition [as …]``.
    capability_names: dict[str, str] = field(default_factory=dict)
    #: receiver name -> one flag per binding in the module: is it the wrapper?
    bindings: dict[str, list[bool]] = field(default_factory=dict)

    def in_package(self, package: str) -> bool:
        return self.module_name == package or self.module_name.startswith(package + ".")

    # -- name resolution -----------------------------------------------------

    def simple(self, name: str) -> str:
        return self.names.get(name, name)

    def head(self, node: ast.expr | None) -> str | None:
        """The simple head name of an annotation or callee expression.

        ``Authorized[X]`` -> ``Authorized``; ``capability.Authorized`` ->
        ``Authorized``; ``Cap`` (an alias) -> ``Authorized``; a quoted forward
        reference is parsed and read the same way. ``None`` when the
        expression has no name at its head (a call, a literal, a lambda).
        """
        node = _unquote(node)
        if isinstance(node, ast.Name):
            return self.simple(node.id)
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Subscript):
            return self.head(node.value)
        return None

    def dotted(self, node: ast.expr) -> str | None:
        """The dotted path an attribute chain denotes, module aliases resolved."""
        if isinstance(node, ast.Name):
            return self.modules.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            base = self.dotted(node.value)
            return f"{base}.{node.attr}" if base else None
        return None

    def members(self, annotation: ast.expr | None) -> list[ast.expr | None]:
        """The union members of an annotation; ``None`` stands for ``NoneType``.

        ``X | None`` -> ``[X, None]``; ``Optional[X]`` -> ``[X, None]``;
        ``Union[A, B]`` -> ``[A, B]``; ``Annotated[X, …]`` -> members of ``X``;
        anything else is one member. ``Callable[[Authorized], None]`` is one
        member with head ``Callable`` — a callback is not an authority
        parameter.
        """
        node = _unquote(annotation)
        if node is None:
            return []
        if isinstance(node, ast.Constant) and node.value is None:
            return [None]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self.members(node.left) + self.members(node.right)
        if isinstance(node, ast.Subscript):
            head = self.head(node.value)
            elts = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            if head == "Optional":
                return [m for e in elts for m in self.members(e)] + [None]
            if head == "Union":
                return [m for e in elts for m in self.members(e)]
            if head == "Annotated" and elts:
                return self.members(elts[0])
        return [node]

    # -- rule-4 receiver proof -----------------------------------------------

    def is_guard_construction(self, node: ast.expr) -> bool:
        return isinstance(node, ast.Call) and self.head(node.func) == TENANT_GUARD_CLASS

    def is_guard_annotation(self, annotation: ast.expr | None) -> bool:
        return annotation is not None and self.head(annotation) == TENANT_GUARD_CLASS

    def is_guarded_receiver(self, node: ast.expr) -> bool:
        if self.is_guard_construction(node):
            return True
        if not isinstance(node, ast.Name):
            return False
        flags = self.bindings.get(node.id, [])
        return bool(flags) and all(flags)


def _unquote(node: ast.expr | None) -> ast.expr | None:
    """A quoted forward reference as the expression it quotes; else as given."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            return ast.parse(node.value, mode="eval").body
        except SyntaxError:
            return None
    return node


def _resolve_imports(ctx: _Module) -> None:
    package = package_for(ctx.path, ctx.module_name)
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                ctx.modules[local] = alias.asname and alias.name or local
        elif isinstance(node, ast.ImportFrom):
            source = _import_source(node, package)
            for alias in node.names:
                local = alias.asname or alias.name
                ctx.names[local] = alias.name
                if source:
                    ctx.modules[local] = f"{source}.{alias.name}"
                    if source in CAPABILITY_SPELLINGS and alias.name in MINT_SYMBOLS:
                        ctx.capability_names[local] = alias.name


def _import_source(node: ast.ImportFrom, package: str) -> str | None:
    if not node.level:
        return node.module
    if not package:
        return None
    parts = package.split(".")
    kept = len(parts) - (node.level - 1)
    if kept <= 0:
        return None
    base = ".".join(parts[:kept])
    return f"{base}.{node.module}" if node.module else base


def _record(ctx: _Module, target: ast.expr, guarded: bool) -> None:
    if isinstance(target, ast.Name):
        ctx.bindings.setdefault(target.id, []).append(guarded)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _record(ctx, elt, False)
    elif isinstance(target, ast.Starred):
        _record(ctx, target.value, False)


def _collect_bindings(ctx: _Module) -> None:
    """Every binding of every name, flagged by whether it is the wrapper.

    Default-deny: a binding form this walk does not read (a ``match``
    capture, ``from x import *``) records nothing, and a receiver with no
    recorded binding is not guarded.
    """
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Assign):
            guarded = ctx.is_guard_construction(node.value)
            for target in node.targets:
                _record(ctx, target, guarded)
        elif isinstance(node, ast.AnnAssign):
            guarded = ctx.is_guard_annotation(node.annotation) or (
                node.value is not None and ctx.is_guard_construction(node.value)
            )
            _record(ctx, node.target, guarded)
        elif isinstance(node, ast.NamedExpr):
            _record(ctx, node.target, ctx.is_guard_construction(node.value))
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            _record(ctx, node.target, False)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    _record(ctx, item.optional_vars, False)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for arg in _all_args(node.args):
                ctx.bindings.setdefault(arg.arg, []).append(
                    ctx.is_guard_annotation(arg.annotation)
                )
            if not isinstance(node, ast.Lambda):
                ctx.bindings.setdefault(node.name, []).append(False)
        elif isinstance(node, ast.ClassDef):
            ctx.bindings.setdefault(node.name, []).append(False)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                ctx.bindings.setdefault(local, []).append(False)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            ctx.bindings.setdefault(node.name, []).append(False)


def _all_args(args: ast.arguments) -> list[ast.arg]:
    return [*args.posonlyargs, *args.args, *args.kwonlyargs]


# --- parameters (rules 1 and 2) -------------------------------------------------


@dataclass(frozen=True)
class _Parameter:
    owner: str
    name: str
    annotation: ast.expr | None
    has_default: bool
    lineno: int


def _parameters(ctx: _Module) -> Iterator[_Parameter]:
    """Every function/lambda parameter and every class-body field, with the
    qualified name of what owns it."""

    def walk(node: ast.AST, stack: tuple[str, ...]) -> Iterator[_Parameter]:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            owner = ".".join(
                (*stack, "<lambda>" if isinstance(node, ast.Lambda) else node.name)
            )
            args = node.args
            positional = [*args.posonlyargs, *args.args]
            defaulted = set(range(len(positional) - len(args.defaults), len(positional)))
            for index, arg in enumerate(positional):
                yield _Parameter(owner, arg.arg, arg.annotation, index in defaulted, arg.lineno)
            for arg, default in zip(args.kwonlyargs, args.kw_defaults):
                yield _Parameter(owner, arg.arg, arg.annotation, default is not None, arg.lineno)
            inner = stack if isinstance(node, ast.Lambda) else (*stack, node.name)
            for child in ast.iter_child_nodes(node):
                yield from walk(child, inner)
            return
        if isinstance(node, ast.ClassDef):
            inner = (*stack, node.name)
            for child in node.body:
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    yield _Parameter(
                        node.name,
                        child.target.id,
                        child.annotation,
                        child.value is not None,
                        child.lineno,
                    )
            for child in ast.iter_child_nodes(node):
                yield from walk(child, inner)
            return
        for child in ast.iter_child_nodes(node):
            yield from walk(child, stack)

    yield from walk(ctx.tree, ())


def _is_authority(ctx: _Module, parameter: _Parameter) -> bool:
    if parameter.name in AUTHORITY_PARAM_NAMES:
        return True
    return any(
        ctx.head(member) in AUTHORITY_TYPES
        for member in ctx.members(parameter.annotation)
        if member is not None
    )


def _rule_default(ctx: _Module) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    for parameter in _parameters(ctx):
        if parameter.has_default and _is_authority(ctx, parameter):
            findings.append(
                (
                    parameter.lineno,
                    f"parameter {parameter.name!r} of {parameter.owner} is an"
                    f" authority parameter ({_render(parameter.annotation)}) and"
                    " carries a default; a capability that may be omitted is"
                    " D-IMPL-73's shape — the seam every caller may decline"
                    " (D-IMPL-353 §4 rule 1)",
                )
            )
    return findings


def _weakness(ctx: _Module, parameter: _Parameter) -> str | None:
    """Why the parameter's type admits absence or anything, or ``None``."""
    if parameter.annotation is None:
        return "has no annotation"
    members = ctx.members(parameter.annotation)
    if None in members:
        return f"admits None ({_render(parameter.annotation)})"
    heads = [ctx.head(member) for member in members if member is not None]
    if any(head in WEAK_HEADS for head in heads) and ctx.module_name != CAPABILITY_MODULE:
        return f"is typed {_render(parameter.annotation)}, which admits anything"
    for member in members:
        node = _unquote(member)
        if node is None or ctx.head(node) != AUTHORIZED_NAME:
            continue
        if not isinstance(node, ast.Subscript):
            return "is a bare Authorized, a capability of no kind"
        if ctx.head(node.slice) in KINDLESS_SLICES:
            return f"is {_render(node)}, a capability of every kind"
    return None


def _rule_weak_type(ctx: _Module) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    for parameter in _parameters(ctx):
        if not _is_authority(ctx, parameter):
            continue
        weakness = _weakness(ctx, parameter)
        if weakness is not None:
            findings.append(
                (
                    parameter.lineno,
                    f"parameter {parameter.name!r} of {parameter.owner} {weakness};"
                    " an authority parameter has exactly one type, the capability"
                    " for its own action, and a type that admits absence is an"
                    " authorization that may not happen (D-IMPL-353 §4 rule 2)",
                )
            )
    return findings


def _render(annotation: ast.expr | None) -> str:
    return "unannotated" if annotation is None else ast.unparse(annotation)


# --- rule 3: a third mint site -------------------------------------------------


def _rule_mint_site(ctx: _Module) -> list[tuple[int, str]]:
    if ctx.module_name == CAPABILITY_MODULE:
        return []
    findings: list[tuple[int, str]] = []
    permitted = {
        MINT_NAME: ctx.module_name in MINT_SITES,
        COMPOSITION_MINT_NAME: ctx.module_name in COMPOSITION_MINT_SITES,
    }
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Call):
            symbol = _capability_producer(ctx, node.func)
            if ctx.head(node.func) == AUTHORIZED_NAME:
                findings.append(
                    (
                        node.lineno,
                        f"constructs {AUTHORIZED_NAME} outside {CAPABILITY_MODULE};"
                        " the authorization gate is the only producer of a"
                        " capability (D-IMPL-353 §1.1)",
                    )
                )
            elif symbol == MINT_NAME and not permitted[symbol]:
                findings.append(
                    (
                        node.lineno,
                        f"calls {CAPABILITY_MODULE}.{MINT_NAME} from"
                        f" {ctx.module_name}, a third mint site; exactly two"
                        " exist, the HTTP gate and the MCP wrapper, and the"
                        " runtime shim that re-exports the name is neither"
                        " (D-IMPL-353 §1.1)",
                    )
                )
            elif symbol == COMPOSITION_MINT_NAME and not permitted[symbol]:
                findings.append(
                    (
                        node.lineno,
                        f"calls {CAPABILITY_MODULE}.{COMPOSITION_MINT_NAME} from"
                        f" {ctx.module_name}; the governed-record mint is the"
                        " composition root's act at boot, and no door and no"
                        " wiring package may hand a served surface a ReplayMint"
                        " (D-IMPL-353 §2 P3)",
                    )
                )
        if isinstance(node, _SENTINEL_HOSTS) and _names_sentinel(node):
            findings.append(
                (
                    node.lineno,
                    f"names {SENTINEL_NAME} outside {CAPABILITY_MODULE}; the"
                    " mint is module-private and its identity is the proof"
                    " (D-IMPL-353 §1.1)",
                )
            )
    return findings


def _capability_producer(ctx: _Module, func: ast.expr) -> str | None:
    """Which capability producer ``func`` denotes — ``"mint"``,
    ``"mint_at_composition"`` — or ``None`` when it is neither.

    Resolved through the import, under either spelling of the capability
    module: a bare name bound by ``from … import mint [as m]``, or an
    attribute on a name bound to the definer or the shim (``cap.mint``,
    ``capability.mint``, ``ccf.authz.capability.mint``). A ``mint`` attribute
    on any other receiver is some other object's method.
    """
    if isinstance(func, ast.Name):
        return ctx.capability_names.get(func.id)
    if isinstance(func, ast.Attribute) and func.attr in MINT_SYMBOLS:
        if ctx.dotted(func.value) in CAPABILITY_SPELLINGS:
            return func.attr
    return None


#: The node kinds a sentinel reference can live in — each carries a line.
_SENTINEL_HOSTS = (ast.Name, ast.Attribute, ast.ImportFrom, ast.Constant)


def _names_sentinel(node: ast.Name | ast.Attribute | ast.ImportFrom | ast.Constant) -> bool:
    if isinstance(node, ast.Name):
        return node.id == SENTINEL_NAME
    if isinstance(node, ast.Attribute):
        return node.attr == SENTINEL_NAME
    if isinstance(node, ast.ImportFrom):
        return any(alias.name == SENTINEL_NAME for alias in node.names)
    return node.value == SENTINEL_NAME


# --- rule 4: raw MCP registration ----------------------------------------------


def _rule_raw_registration(ctx: _Module) -> list[tuple[int, str]]:
    if ctx.module_name == TENANT_GUARD_MODULE:
        return []
    findings: list[tuple[int, str]] = []
    seen: set[int] = set()
    for node in ast.walk(ctx.tree):
        candidates: list[ast.expr] = []
        if isinstance(node, ast.Call):
            candidates.append(node.func)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            candidates.extend(d for d in node.decorator_list if not isinstance(d, ast.Call))
        for candidate in candidates:
            if not (isinstance(candidate, ast.Attribute) and candidate.attr in REGISTRATION_METHODS):
                continue
            if ctx.is_guarded_receiver(candidate.value) or id(candidate) in seen:
                continue
            seen.add(id(candidate))
            findings.append(
                (
                    candidate.lineno,
                    f"registers an MCP {candidate.attr} on"
                    f" {ast.unparse(candidate.value)!r}, which is not provably a"
                    f" {TENANT_GUARD_CLASS}; a surface registered outside the"
                    " wrapper has no capability to hand any handle"
                    " (D-IMPL-353 §2 P9, §4 rule 4)",
                )
            )
    return findings


# --- rule 5: an undeclared route -----------------------------------------------


def _decorator_head(decorator: ast.expr) -> ast.expr:
    return decorator.func if isinstance(decorator, ast.Call) else decorator


def _route_verb(decorator: ast.expr) -> str | None:
    head = _decorator_head(decorator)
    if isinstance(head, ast.Attribute) and head.attr in ROUTE_VERBS:
        return head.attr
    return None


def _is_authorizes(ctx: _Module, decorator: ast.expr) -> bool:
    head = _decorator_head(decorator)
    if isinstance(head, ast.Name):
        return ctx.simple(head.id) == AUTHORIZES_NAME
    return isinstance(head, ast.Attribute) and head.attr == AUTHORIZES_NAME


def _rule_unguarded_route(ctx: _Module) -> list[tuple[int, str]]:
    if not ctx.in_package(ROUTES_PACKAGE):
        return []
    findings: list[tuple[int, str]] = []
    for node in ast.walk(ctx.tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            verbs = [v for v in map(_route_verb, node.decorator_list) if v is not None]
            if verbs and not any(_is_authorizes(ctx, d) for d in node.decorator_list):
                findings.append(
                    (
                        node.lineno,
                        f"route handler {node.name!r} is mounted with"
                        f" {', '.join(verbs)} and declares no @{AUTHORIZES_NAME};"
                        " a route with no declaration is one the gate could only"
                        " deny or only allow (SEC-001, D-IMPL-353 §4 rule 5)",
                    )
                )
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in PROGRAMMATIC_ROUTE_METHODS:
                findings.append(
                    (
                        node.lineno,
                        f"registers a route through {func.attr}, whose"
                        " declaration cannot be read statically; routes are"
                        f" declared at their definition with @{AUTHORIZES_NAME}"
                        " (SEC-001, D-IMPL-353 §4 rule 5)",
                    )
                )
    return findings


# --- rule 6: the static tooth overridden ----------------------------------------


def _type_ignore_lines(source: str) -> dict[int, str]:
    """Physical line -> the ``type: ignore`` comment on it, from the token
    stream — so a docstring quoting the phrase is a STRING, not a COMMENT."""
    found: dict[int, str] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and TYPE_IGNORE_COMMENT.search(token.string):
                found[token.start[0]] = token.string.strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return found
    return found


def _authority_spans(ctx: _Module) -> list[tuple[int, int, str]]:
    """``(first line, last line, what)`` for every node an ignore must not sit in."""
    spans: list[tuple[int, int, str]] = []
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Call):
            reasons: list[str] = []
            for keyword in node.keywords:
                if keyword.arg is None:
                    reasons.append("a ** splat, whose keys the type checker cannot read")
                elif keyword.arg in AUTHORITY_PARAM_NAMES:
                    reasons.append(f"keyword {keyword.arg!r}")
            if any(isinstance(arg, ast.Starred) for arg in node.args):
                reasons.append("a * splat, whose members the type checker cannot read")
            if reasons:
                callee = ctx.head(node.func) or ast.unparse(node.func)
                spans.append(
                    (
                        node.lineno,
                        node.end_lineno or node.lineno,
                        f"a call to {callee!r} passing {', '.join(reasons)}",
                    )
                )
        elif isinstance(node, ast.AnnAssign):
            if any(
                ctx.head(member) in AUTHORITY_TYPES
                for member in ctx.members(node.annotation)
                if member is not None
            ):
                spans.append(
                    (
                        node.lineno,
                        node.end_lineno or node.lineno,
                        f"an assignment annotated {ast.unparse(node.annotation)}",
                    )
                )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            owner = node.name
            authority = [
                arg.arg
                for arg in _all_args(node.args)
                if _is_authority(ctx, _Parameter(owner, arg.arg, arg.annotation, False, arg.lineno))
            ]
            if authority and node.body:
                spans.append(
                    (
                        node.lineno,
                        node.body[0].lineno - 1,
                        f"the signature of {owner!r}, which takes {', '.join(map(repr, authority))}",
                    )
                )
    return spans


def _rule_type_ignore(ctx: _Module) -> list[tuple[int, str]]:
    ignores = _type_ignore_lines(ctx.source)
    if not ignores:
        return []
    spans = _authority_spans(ctx)
    findings: list[tuple[int, str]] = []
    for line, comment in sorted(ignores.items()):
        for start, end, what in spans:
            if start <= line <= end:
                findings.append(
                    (
                        line,
                        f"overrides the type checker ({comment}) inside {what};"
                        " the kind is the type and the type is the static tooth,"
                        " so an ignore here is a capability forced past it"
                        " (D-IMPL-353 §1.5b, §4 rule 6)",
                    )
                )
                break
    return findings


# --- dispatch --------------------------------------------------------------------

#: The six rules, by id. ``check_source`` runs every entry; a test severs one
#: entry at a time and asserts that exactly that rule's findings disappear.
RULES: tuple[tuple[str, Callable[[_Module], list[tuple[int, str]]]], ...] = (
    (RULE_DEFAULT, _rule_default),
    (RULE_WEAK_TYPE, _rule_weak_type),
    (RULE_MINT_SITE, _rule_mint_site),
    (RULE_RAW_REGISTRATION, _rule_raw_registration),
    (RULE_UNGUARDED_ROUTE, _rule_unguarded_route),
    (RULE_TYPE_IGNORE, _rule_type_ignore),
)


def check_source(source: str, path: pathlib.Path, module_name: str) -> list[str]:
    """Run every rule over `source`; findings sorted by line, then rule id."""
    ctx = _Module(
        tree=read_tree(source, path), path=path, module_name=module_name, source=source
    )
    _resolve_imports(ctx)
    _collect_bindings(ctx)
    collected: list[tuple[int, str, str]] = []
    for rule, run_rule in RULES:
        collected.extend((lineno, rule, message) for lineno, message in run_rule(ctx))
    collected.sort()
    return [format_finding(path, lineno, rule, message) for lineno, rule, message in collected]


def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
