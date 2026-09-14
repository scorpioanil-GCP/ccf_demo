"""D-IMPL-337 census v2 — find guarded-type USE, not merely annotation.

Census v1 keyed on parameter annotations. That instrument has two measured
blind spots, and both matter to the design:

  * a consumer that takes ``object`` DELIBERATELY is invisible to it —
    ``ccf.products.composite.compose_children`` is exactly that, and it DOES
    verify ``AdmittedChild`` with ``isinstance``;
  * a consumer that verifies by some means other than a literal ``isinstance``
    would be reported as trusting the annotation.

So v2 measures three things per guarded type: who *names* it, who *verifies*
it by any detectable means, and who can be *reached from outside the module*.
"""

from __future__ import annotations

import ast
import pathlib
from collections import defaultdict

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"


def _module(path: pathlib.Path) -> str:
    return str(path.relative_to(SRC))


def guarded_types() -> dict[str, tuple[str, str]]:
    """Classes whose ``__init__`` refuses without a module-private token."""
    found: dict[str, tuple[str, str]] = {}
    for f in SRC.rglob("*.py"):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not (isinstance(item, ast.FunctionDef) and item.name == "__init__"):
                    continue
                for sub in ast.walk(item):
                    if isinstance(sub, ast.If) and "token is not" in ast.unparse(sub.test):
                        raised = [
                            ast.unparse(r.exc).split("(")[0]
                            for r in ast.walk(sub)
                            if isinstance(r, ast.Raise) and r.exc
                        ]
                        found[node.name] = (_module(f), raised[0] if raised else "?")
    return found


def _exports(tree: ast.Module) -> set[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "__all__" for t in node.targets
        ):
            try:
                return set(ast.literal_eval(node.value))
            except Exception:
                return set()
    return set()


def survey() -> None:
    caps = guarded_types()
    print(f"GUARDED TYPES: {len(caps)}")
    for name, (mod, err) in sorted(caps.items()):
        print(f"  {name:20s} {mod:34s} raises {err}")

    rows: dict[str, list[tuple]] = defaultdict(list)
    for f in SRC.rglob("*.py"):
        text = f.read_text()
        tree = ast.parse(text)
        exports = _exports(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = ast.unparse(node)
            for cap in caps:
                # NAMED: annotated as a parameter (census v1's whole universe)
                named = any(
                    a.annotation is not None
                    and ast.unparse(a.annotation).replace('"', "").replace("'", "")
                    in (cap, f"{cap} | None")
                    for a in list(node.args.args) + list(node.args.kwonlyargs)
                )
                # VERIFIED: any detectable runtime check against the type
                verified = (
                    f"isinstance" in body and cap in body
                ) or f"type({cap}" in body
                # USED: the name appears at all (construction, check, or hint)
                used = cap in body
                if not used:
                    continue
                reach = (
                    "EXPORTED" if node.name in exports
                    else "module-private" if node.name.startswith("_")
                    else "public-name"
                )
                rows[cap].append((_module(f), node.name, named, verified, reach))

    print("\nUSE SITES (named OR verified OR constructed):")
    total = exposed_unverified = 0
    for cap in sorted(rows):
        print(f"\n  {cap}:")
        for mod, fn, named, verified, reach in sorted(set(rows[cap])):
            total += 1
            flag = "VERIFIES" if verified else ("names-only" if named else "mentions")
            gap = reach != "module-private" and not verified and named
            if gap:
                exposed_unverified += 1
            mark = "  <-- EXPOSED, UNVERIFIED" if gap else ""
            print(f"     {flag:11s} {reach:14s} {mod}::{fn}{mark}")
    print(f"\nTOTAL use sites: {total}")
    print(f"EXPOSED AND UNVERIFIED (annotated, reachable, no check): {exposed_unverified}")


if __name__ == "__main__":
    survey()
