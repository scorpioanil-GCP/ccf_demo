"""D-IMPL-337 census v3 — precise: does THIS parameter get checked against THIS type?

v1 keyed on `isinstance(<arg>` appearing as text and reported 14 of 15 sites as
unverified. v2 keyed on `isinstance` appearing anywhere alongside the type name
and reported only 3. **Both are wrong, in opposite directions**, and reading
the disputed sites settled it:

  * v1 MISSES real verification — `compose_children` takes ``outcomes: object``
    deliberately and does verify ``AdmittedChild``, so an annotation-keyed
    instrument cannot see it;
  * v2 OVER-CREDITS — `mount_product_source` isinstance-checks the payload
    shape, and `refuse_over_tolerance` isinstance-checks a tolerance value;
    neither checks the guarded parameter it was credited for.

v3 asks the exact question: for a parameter ``p`` annotated ``T`` where ``T``
is guarded, does the body contain ``isinstance(p, ...T...)``? It also reports
guarded types VERIFIED without being annotated, which is the shape v1 could
not represent at all.

**This instrument is evidence for the D-IMPL-337 design, not the rule.** Its
own false-positive and false-negative boundary is one of the eight questions
the design must answer.
"""

from __future__ import annotations

import ast
import pathlib
from collections import defaultdict

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"


def guarded_types() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        if any(
                            isinstance(s, ast.If) and "token is not" in ast.unparse(s.test)
                            for s in ast.walk(item)
                        ):
                            out[node.name] = str(f.relative_to(SRC))
    return out


def _checks(fn: ast.AST, arg: str, cap: str) -> bool:
    """Is there a literal ``isinstance(arg, ...cap...)`` in this function?"""
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "isinstance"):
            continue
        if not node.args or getattr(node.args[0], "id", None) != arg:
            continue
        second = ast.unparse(node.args[1]) if len(node.args) > 1 else ""
        if cap in second:
            return True
    return False


def _verifies_any(fn: ast.AST, cap: str) -> str | None:
    """Any ``isinstance(<something>, cap)`` — catches unannotated verification."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "isinstance":
            if len(node.args) > 1 and cap in ast.unparse(node.args[1]):
                return ast.unparse(node.args[0])
    return None


def survey() -> None:
    caps = guarded_types()
    annotated: dict[str, list] = defaultdict(list)
    unannotated: dict[str, list] = defaultdict(list)

    for f in SRC.rglob("*.py"):
        tree = ast.parse(f.read_text())
        exports: set[str] = set()
        for n in tree.body:
            if isinstance(n, ast.Assign) and any(
                getattr(t, "id", "") == "__all__" for t in n.targets
            ):
                try:
                    exports = set(ast.literal_eval(n.value))
                except Exception:
                    pass
        mod = str(f.relative_to(SRC))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # A dunder is NOT private: `__init__` of an exported class is
            # reachable by anyone who can name the class. Census v3 filed
            # `ProductSource.__init__` as module-private on the strength of
            # the leading underscore and missed a governed site — the
            # instrument's own false-negative, found by review.
            dunder = node.name.startswith("__") and node.name.endswith("__")
            reach = (
                "EXPORTED" if node.name in exports
                else "constructor" if dunder
                else "module-private" if node.name.startswith("_")
                else "public-name"
            )
            seen: set[str] = set()
            for a in list(node.args.args) + list(node.args.kwonlyargs):
                if a.annotation is None:
                    continue
                ann = ast.unparse(a.annotation).replace('"', "").replace("'", "")
                for cap in caps:
                    if ann in (cap, f"{cap} | None"):
                        seen.add(cap)
                        annotated[cap].append(
                            (mod, node.name, a.arg, _checks(node, a.arg, cap), reach)
                        )
            for cap in caps:
                if cap in seen:
                    continue
                subject = _verifies_any(node, cap)
                if subject is not None:
                    unannotated[cap].append((mod, node.name, subject, reach))

    print(f"GUARDED TYPES: {len(caps)}\n")
    print("A. ANNOTATED CONSUMERS — does the body check THAT parameter against THAT type?")
    gaps = []
    for cap in sorted(annotated):
        print(f"\n  {cap}:")
        for mod, fn, arg, ok, reach in sorted(set(annotated[cap])):
            mark = "CHECKS" if ok else "no check"
            if not ok and reach != "module-private":
                gaps.append((cap, mod, fn, arg, reach))
            print(f"     {mark:9s} {reach:14s} {mod}::{fn}({arg})")

    print("\n\nB. VERIFICATION WITHOUT ANNOTATION — invisible to an annotation-keyed census")
    for cap in sorted(unannotated):
        for mod, fn, subject, reach in sorted(set(unannotated[cap])):
            print(f"     CHECKS {cap:18s} {reach:14s} {mod}::{fn}  (subject: {subject})")

    print(f"\n\nC. EXPOSED AND UNCHECKED — the governed population, by this instrument: {len(gaps)}")
    for cap, mod, fn, arg, reach in gaps:
        print(f"     {cap:18s} {reach:14s} {mod}::{fn}({arg})")


if __name__ == "__main__":
    survey()
