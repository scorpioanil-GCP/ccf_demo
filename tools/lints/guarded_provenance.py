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
import pathlib

RULE = "guarded-provenance"

#: Where guarded types and their boundaries may live. `examples/` is excluded
#: deliberately: frozen specimens are not authority checks (CLAUDE.md §9,
#: `D-IMPL-261`), and a lint that reached them would force edits this project
#: forbids.
TREES = ("src", "runtime")


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


def check_tree(base: pathlib.Path) -> list[str]:
    """Findings only, in the shared format."""
    from ccf.contracts.guarded import GUARDED_TYPES

    declared = {d.type_path: d for d in GUARDED_TYPES}
    findings: list[str] = []
    sources: dict[str, ast.Module] = {}

    for tree_name in TREES:
        root = base / tree_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                module = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
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
