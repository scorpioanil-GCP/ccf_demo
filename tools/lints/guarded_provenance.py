"""`D-IMPL-337` drift: declared guarded types and boundaries vs. what is there.

**The declaration is the truth; this checker only reports drift against it.**
That ordering is the whole design and it was paid for: the AST census that
found this class of defect was wrong three separate times — it under-counted
verification, then over-credited it, then filed the constructor of an exported
class as module-private because the function name begins with an underscore.
A checker built as the semantic rule would have shipped each of those errors
as law.

So this checker asks only questions a scan can answer honestly:

* a class whose construction is token-guarded and that **declares nothing** —
  the drift that matters, and the reason guarded type #8 cannot arrive
  silently with a different mint style;
* a declared type whose ``type_path``, ``mint``, ``verifier`` or
  ``boundaries`` **do not resolve** to anything in the tree;
* a declared boundary that does not **call** its type's declared verifier.

**What it deliberately does NOT do**, because `D-IMPL-337` forbids keying
enforcement on any of them: it does not read annotations, does not infer
governance from a leading underscore, does not look for literal ``isinstance``
syntax, does not treat Protocol conformance as authority, and does not credit
or penalize PEP 634 class patterns. A frozen example that pattern-matches on a
guarded type is not making an authority claim and is not reached here — which
is why this checker scans ``src/`` and ``runtime/`` and never ``examples/``.
"""

from __future__ import annotations

import ast
import dataclasses
import pathlib

RULE = "guarded-provenance"

#: Where guarded types and their boundaries may live. `examples/` is excluded
#: deliberately: frozen specimens are not authority checks (CLAUDE.md §9,
#: `D-IMPL-261`), and a lint that reached them would force edits this project
#: forbids.
TREES = ("src", "runtime")

#: Where the registry lives under a base tree. Read from ``--base``, never from
#: the process's importable ``ccf``: the runner's contract is that every rule
#: reads the tree it is pointed at and that a tree without ``src`` is skipped,
#: and importing the installed package made this rule the one exception — on
#: any base but the real repository every declaration named a module absent
#: from the census, and a clean fixture failed the gate (release qualification
#: of `f0656746`, `tools/lints/tests/test_runner.py` red since `c676603f`).
REGISTRY = pathlib.Path("src") / "ccf" / "contracts" / "guarded.py"


def _finding(path: str, line: int, message: str) -> str:
    return f"{path}:{line} {RULE} {message}"


def _token_guarded(tree: ast.Module) -> list[tuple[str, int]]:
    """Classes whose ``__init__`` refuses without a module-private token.

    A HEURISTIC, and labelled as one: it matches the spelling the existing
    types happen to share. A guarded type minting some other way is invisible
    here — which is exactly why declaration is mandatory rather than inferred.
    """
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not (isinstance(item, ast.FunctionDef) and item.name == "__init__"):
                continue
            for sub in ast.walk(item):
                if isinstance(sub, ast.If) and "token is not" in ast.unparse(sub.test):
                    out.append((node.name, node.lineno))
    return out


def _module_name(path: pathlib.Path, base: pathlib.Path) -> str:
    rel = path.relative_to(base)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[0] in TREES:
        parts = parts[1:]
    return ".".join(parts)


@dataclasses.dataclass(frozen=True)
class _Declaration:
    """One ``GuardedTypeDeclaration(...)`` as READ from the registry's source.

    The fields the rule consults, taken from the call's keyword literals; the
    prose fields (``authority``, ``propagation``, ``residual``, ``notes``) are
    not needed for drift checking and are not read.
    """

    type_path: str
    verifier: str | None = None
    boundaries: tuple[str, ...] = ()
    verifier_aliases: tuple[str, ...] = ()


_CONSULTED = ("type_path", "verifier", "boundaries", "verifier_aliases")
_TUPLE_FIELDS = {"boundaries", "verifier_aliases"}


def _literal(node: ast.expr) -> str | None | tuple[str, ...]:
    """A string, ``None`` or a tuple of strings — the only shapes a field takes."""
    if isinstance(node, ast.Constant) and (node.value is None or isinstance(node.value, str)):
        return node.value
    if isinstance(node, ast.Tuple):
        members = [e.value for e in node.elts if isinstance(e, ast.Constant)]
        if len(members) == len(node.elts) and all(isinstance(m, str) for m in members):
            return tuple(m for m in members if isinstance(m, str))
    raise ValueError(
        f"line {node.lineno}: {ast.unparse(node)!r} is not a string, None or tuple of strings"
    )


def _declared_fields(module: ast.Module) -> tuple[set[str], set[str]] | None:
    """``(known, required)`` field names of ``GuardedTypeDeclaration``, from its class body.

    Read from the same file so the rule follows the tree it is pointed at: an
    annotated class attribute is a field; one without a default is required.
    """
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == "GuardedTypeDeclaration":
            known: set[str] = set()
            required: set[str] = set()
            for item in node.body:
                if not (isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)):
                    continue
                annotation = ast.unparse(item.annotation)
                if "ClassVar" in annotation or "KW_ONLY" in annotation:
                    continue  # not an init field, as dataclasses reads them
                known.add(item.target.id)
                if item.value is None or _is_field_call_without_default(item.value):
                    required.add(item.target.id)
            return known, required
    return None


def _is_field_call_without_default(value: ast.expr) -> bool:
    """``field(...)`` / ``dataclasses.field(...)`` with no usable default — still required.

    ``default=MISSING`` is dataclasses' own spelling of "no default" and counts
    as none; ``default_factory`` counts as a default.
    """
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    is_field = (isinstance(func, ast.Name) and func.id == "field") or (
        isinstance(func, ast.Attribute) and func.attr == "field"
    )
    if not is_field:
        return False
    for keyword in value.keywords:
        if keyword.arg == "default_factory":
            return False
        if keyword.arg == "default":
            missing = isinstance(keyword.value, ast.Name) and keyword.value.id == "MISSING"
            missing = missing or (isinstance(keyword.value, ast.Attribute) and keyword.value.attr == "MISSING")
            return missing
    return True


def _bound_names(node: ast.AST) -> set[str]:
    """Names ``node`` binds or rebinds, for the one-binding rule."""
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign, ast.NamedExpr)):
        if not (isinstance(node, ast.AnnAssign) and node.value is None):
            targets = [node.target]
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        targets = [node.target]
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        targets = [item.optional_vars for item in node.items if item.optional_vars is not None]
    elif isinstance(node, ast.Delete):
        targets = list(node.targets)
    names: set[str] = set()
    for target in targets:
        for sub in ast.walk(target):
            if isinstance(sub, ast.Name):
                names.add(sub.id)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        names.add(node.name)
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        names.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        names.update(node.names)
    if isinstance(node, ast.ExceptHandler) and node.name:
        names.add(node.name)
    if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
        names.add(node.name)
    if isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
        names.add(node.name.id)
    if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
        names.add("GUARDED_TYPES")  # a star import may rebind anything; refused as unfollowable
    return names


def _names_registry(targets: list[ast.expr]) -> bool:
    return any(isinstance(t, ast.Name) and t.id == "GUARDED_TYPES" for t in targets)


def _load_registry(base: pathlib.Path) -> tuple[_Declaration, ...] | str:
    """The declarations under ``base``, read from source — never executed.

    No registry under ``base`` means no declarations (the token-guarded census
    still runs, so an undeclared class is still reported). Everything else that
    is not a clean read is returned as text and reported as ONE finding —
    never a skip, never an exception out of the gate: a registry that cannot
    be read or parsed (any error, a BOM is fine), no module-level
    ``GUARDED_TYPES`` binding, more than one binding or an in-place extension
    (``+=``), a value that is not a tuple literal of keyword-only
    ``GuardedTypeDeclaration(...)`` calls, a ``**`` splat, a repeated or unknown
    keyword, a missing required field, or a consulted field that is not a
    string / ``None`` / tuple-of-strings literal of the shape the field takes.
    The known and required fields come from the ``GuardedTypeDeclaration`` class
    body in the same file, by the dataclass's rule as far as a parser can follow
    it (a plain ``field(...)`` spelling; an aliased import of ``field`` or
    ``KW_ONLY`` is read conservatively and may be refused where Python would
    accept). The one-binding rule covers every parser-visible rebinding; what no
    static reader can see (``exec``, ``setattr`` on the module) is out of reach,
    and a class-body attribute named ``GUARDED_TYPES`` is refused although it
    does not rebind the module name — a loud false refusal, never a silent
    read. Nothing under ``--base`` is imported or run.
    """
    path = base / REGISTRY
    try:
        if not (path.exists() or path.is_symlink()):
            return ()
        if not path.is_file():
            raise OSError("not a regular file")
        module = ast.parse(path.read_bytes(), filename=str(path))
    except Exception as error:  # noqa: BLE001 — every read or parse failure is a finding
        return f"{type(error).__name__}: {error}"
    # The one-binding rule, over the WHOLE file: a `+=`, a second assignment, a
    # loop or `with` target, a `global` declaration, an import or a def named
    # GUARDED_TYPES anywhere — inside a block or a function included — is a
    # rebinding the rule cannot follow and is refused, never silently skipped.
    binding: tuple[int, ast.expr] | None = None
    rebinding: list[int] = []
    for node in ast.walk(module):
        if "GUARDED_TYPES" not in _bound_names(node):
            continue
        at_module_level = node in module.body
        if at_module_level and binding is None and isinstance(node, ast.Assign) and _names_registry(node.targets):
            binding = (node.lineno, node.value)
        elif (
            at_module_level
            and binding is None
            and isinstance(node, ast.AnnAssign)
            and node.value is not None
            and _names_registry([node.target])
        ):
            binding = (node.lineno, node.value)
        else:
            rebinding.append(getattr(node, "lineno", 0))
    if rebinding:
        lines = ", ".join(str(n) for n in sorted(rebinding))
        return f"GUARDED_TYPES is bound more than once or rebound (lines {lines}); the rule reads one module-level tuple literal"
    if binding is None:
        return "no module-level GUARDED_TYPES assignment"
    bindings = [binding]
    fields_of_class = _declared_fields(module)
    if fields_of_class is None:
        return "no GuardedTypeDeclaration class to read the field set from"
    known, required = fields_of_class
    lineno, value = bindings[0]
    if not isinstance(value, ast.Tuple):
        return f"line {lineno}: GUARDED_TYPES is not a tuple literal"
    declarations: list[_Declaration] = []
    for call in value.elts:
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "GuardedTypeDeclaration"
        ):
            return f"line {call.lineno}: {ast.unparse(call)[:60]!r} is not a GuardedTypeDeclaration(...) call"
        if call.args:
            return f"line {call.lineno}: positional arguments; the rule reads keyword literals"
        given: dict[str, ast.expr] = {}
        for keyword in call.keywords:
            if keyword.arg is None:
                return f"line {call.lineno}: a ** splat; the rule reads keyword literals"
            if keyword.arg in given:
                return f"line {call.lineno}: keyword {keyword.arg!r} is repeated"
            if keyword.arg not in known:
                return f"line {call.lineno}: unknown field {keyword.arg!r}"
            given[keyword.arg] = keyword.value
        missing = sorted(required - set(given))
        if missing:
            return f"line {call.lineno}: declaration is missing required field(s) {missing}"
        read: dict[str, str | None | tuple[str, ...]] = {}
        for name in _CONSULTED:
            if name not in given:
                continue
            try:
                literal = _literal(given[name])
            except ValueError as error:
                return str(error)
            if name in _TUPLE_FIELDS and not isinstance(literal, tuple):
                return f"line {call.lineno}: {name} must be a tuple of strings"
            if name == "type_path" and not isinstance(literal, str):
                return f"line {call.lineno}: type_path must be a string"
            if name == "verifier" and literal is not None and not isinstance(literal, str):
                return f"line {call.lineno}: verifier must be a string or None"
            read[name] = literal
        if "type_path" not in read:
            return f"line {call.lineno}: a declaration carries no type_path; the rule cannot name it"
        declarations.append(_Declaration(**read))  # type: ignore[arg-type]
    return tuple(declarations)


def check_tree(base: pathlib.Path) -> list[str]:
    """Findings only, in the shared format."""
    registry = _load_registry(base)
    if isinstance(registry, str):
        return [
            _finding(
                str(REGISTRY),
                1,
                f"the guarded-type registry could not be read ({registry});"
                " nothing it declares can be checked (D-IMPL-337)",
            )
        ]
    GUARDED_TYPES = registry

    declared = {d.type_path: d for d in GUARDED_TYPES}
    findings: list[str] = []
    sources: dict[str, ast.Module] = {}

    for tree_name in TREES:
        root = base / tree_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                module = ast.parse(path.read_bytes(), filename=str(path))
            except (SyntaxError, ValueError, OSError):
                continue
            mod = _module_name(path, base)
            sources[mod] = module
            rel = str(path.relative_to(base))
            for cls, line in _token_guarded(module):
                key = f"{mod}:{cls}"
                if key not in declared:
                    findings.append(
                        _finding(
                            rel,
                            line,
                            f"{cls!r} is token-guarded and undeclared; add it to"
                            " ccf.contracts.guarded.GUARDED_TYPES with the"
                            " authority it carries, its mint, its verifier and"
                            " its governed boundaries (D-IMPL-337)",
                        )
                    )

    for declaration in GUARDED_TYPES:
        mod, _, name = declaration.type_path.partition(":")
        if mod not in sources:
            findings.append(
                _finding(
                    "src/ccf/contracts/guarded.py",
                    1,
                    f"declared guarded type {declaration.type_path!r} names a"
                    " module that does not exist (D-IMPL-337)",
                )
            )
            continue
        if not _defines(sources[mod], name):
            findings.append(
                _finding(
                    "src/ccf/contracts/guarded.py",
                    1,
                    f"declared guarded type {declaration.type_path!r} does not"
                    " resolve in the tree (D-IMPL-337)",
                )
            )
        if declaration.verifier is None:
            continue
        vmod, _, vname = declaration.verifier.partition(":")
        if vmod not in sources or not _defines(sources[vmod], vname):
            findings.append(
                _finding(
                    "src/ccf/contracts/guarded.py",
                    1,
                    f"declared verifier {declaration.verifier!r} for"
                    f" {declaration.type_path!r} does not resolve (D-IMPL-337)",
                )
            )
            continue
        for boundary in declaration.boundaries:
            bmod, _, bname = boundary.partition(":")
            if bmod not in sources:
                findings.append(
                    _finding(
                        "src/ccf/contracts/guarded.py",
                        1,
                        f"declared boundary {boundary!r} names a module that"
                        " does not exist (D-IMPL-337)",
                    )
                )
                continue
            accepted = {vname} | {
                alias.partition(":")[2].split(".")[-1]
                for alias in declaration.verifier_aliases
            }
            if not any(
                _calls(sources[bmod], bname.split(".")[-1], name)
                for name in accepted
            ):
                findings.append(
                    _finding(
                        f"{_path_of(bmod)}",
                        1,
                        f"declared boundary {boundary!r} does not call its"
                        f" type's declared verifier or any declared alias"
                        f" ({sorted(accepted)}); a boundary that relies on"
                        " guarded authority must establish it (D-IMPL-337)",
                    )
                )
    return findings


def _path_of(mod: str) -> str:
    return "src/" + mod.replace(".", "/") + ".py"


def _defines(tree: ast.Module, qualname: str) -> bool:
    head = qualname.split(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == head:
                return True
    return False


def _calls(tree: ast.Module, func_name: str, callee: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func_name:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                name = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
                if name == callee:
                    return True
    return False
