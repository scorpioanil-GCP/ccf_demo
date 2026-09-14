"""Enumerate the capability surface: token-guarded types, and who consumes them."""
import ast, pathlib, collections

SRC = pathlib.Path("/home/parkave/ccf_code/src")
guarded = {}   # class name -> (file, the error it raises)
for f in SRC.rglob("*.py"):
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not (isinstance(item, ast.FunctionDef) and item.name == "__init__"):
                continue
            # a token guard: `if token is not X: raise ...`
            for sub in ast.walk(item):
                if isinstance(sub, ast.If):
                    src = ast.unparse(sub.test)
                    if "token is not" in src:
                        raised = [ast.unparse(r.exc).split("(")[0]
                                  for r in ast.walk(sub) if isinstance(r, ast.Raise) and r.exc]
                        guarded[node.name] = (str(f.relative_to(SRC)), raised[0] if raised else "?")
print(f"TOKEN-GUARDED CAPABILITY TYPES: {len(guarded)}")
for k, (f, e) in sorted(guarded.items()):
    print(f"  {k:26s} {f:40s} raises {e}")

# who consumes them, by annotation, and does the consumer check?
print("\nCONSUMERS (functions annotating a guarded type as a parameter):")
rows = []
for f in SRC.rglob("*.py"):
    text = f.read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body_src = ast.unparse(node)
        for arg in list(node.args.args) + list(node.args.kwonlyargs):
            if arg.annotation is None:
                continue
            ann = ast.unparse(arg.annotation).replace('"', "").replace("'", "")
            for cap in guarded:
                if cap == ann or ann.startswith(cap + " ") or ann == f"{cap} | None":
                    checks = f"isinstance({arg.arg}" in body_src
                    rows.append((cap, str(f.relative_to(SRC)), node.name, arg.arg, checks))
by_cap = collections.defaultdict(list)
for cap, f, fn, arg, checks in rows:
    by_cap[cap].append((f, fn, arg, checks))
unchecked = 0
for cap in sorted(by_cap):
    print(f"\n  {cap}:")
    for f, fn, arg, checks in by_cap[cap]:
        mark = "checks" if checks else "TRUSTS ANNOTATION"
        if not checks:
            unchecked += 1
        print(f"     {mark:18s} {f}::{fn}({arg})")
print(f"\nTOTAL consumer sites: {len(rows)}   of which trust the annotation only: {unchecked}")
