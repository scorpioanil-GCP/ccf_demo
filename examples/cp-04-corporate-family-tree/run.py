"""The client — **Gate 2 in progress; this driver LOADS the artifacts and stops.**

[ADAPT] all of it. [MECHANISM] nothing.

**WHAT THIS FILE IS RIGHT NOW, STATED PLAINLY SO NOBODY MISTAKES IT FOR THE
DRIVER.** Phase 24.4 builds this example in the order its specification fixes:
specification, then artifacts, then the census harness, then the deployment,
then the assembly, then the two callers, then the gates, then the documentation.
The artifacts are written and the assembly is NOT.

This file exists at this point for one reason, and it is the same reason rung 03
carried a thin driver through its own wave 1: the repository's own gate
(``tests/examples/test_artifact_schema_headers.py::test_every_covered_artifact_directory_sits_under_an_example_root``)
holds that an ``artifacts/`` directory beside no ``run.py`` is not an example,
and that predicate is deliberate and load-bearing rather than an obstacle to
route around. **A red tree carried across a session is worse than a thin driver,
so the driver is thin and says so.** See ``produce.py``'s docstring for the pair
of gates that between them leave no green half-example, and for Dave's ruling.

**WHAT IT DELIBERATELY DOES NOT DO:**

* it does not assemble anything,
* it does not open Fluree, PostgreSQL, or any other store,
* it does not preview ``assembler.py`` or ``deployment.py``, which are not
  written and must not be sketched here, because a sketch is a design decision
  taken in the wrong file.

It reads the five declaration artifacts and prints enough to prove each one
parsed: its class id, the values a later gate will read back out of it, and the
size of the vocabulary it declares. That is the whole contract of this file
until plan ``24.4-08`` replaces it.

**THE QUOTED DECIMAL IS NOT A TYPO, AND THIS FILE ENFORCES IT.**
``debt_tolerance`` is quoted in ``question.yaml`` and prints here exactly as it
parses — as text, not a float. A Control Plane artifact refuses a float because
a float is not bit-stable across platforms, and a value that is not bit-stable
cannot be replayed. Rung 03 met that refusal from three distinct surfaces and
recorded each.

That rule is not merely asserted here. Every loaded artifact is put through
``ccf.contracts.canonical::content_hash``, the fabric's own canonical encoder,
which **raises on a float**. So unquoting the decimal does not produce a subtly
different number that survives review — it stops this driver with a
``CanonicalizationError`` naming the offending value. The digest it returns is
also a stable fingerprint of the artifact set, which is what a later plan will
pin a replay against.

**AND THE DIGEST IS NOT THE PRODUCT'S CONTENT ADDRESS.** It is a fingerprint of
five documents on disk. ``artifacts/expected.yaml`` carries no ``payload_hash``
for exactly this reason: a hash authored beside an expectation is a transcript
of a run, or the suite agreeing with itself.
"""

from __future__ import annotations

import pathlib
import sys

import yaml

from ccf.contracts.canonical import content_hash

ARTIFACTS = pathlib.Path(__file__).resolve().parent / "artifacts"

#: The five declaration artifacts, and the fields a reader should see proved.
#: Names only — every VALUE lives in the YAML, which is the point of the split.
_EXPECTED: dict[str, tuple[str, ...]] = {
    "question.yaml": ("subject", "asked_at", "parameters"),
    "ttl.yaml": ("declared_ttl_seconds", "max_ttl_seconds", "ttl_anchor_basis"),
    "expected.yaml": ("operators_invoked_expected", "census", "wrong_methods"),
    "assembly-recipe.yaml": ("operator_vocabulary", "witness_kinds", "steps"),
    "gates.yaml": ("product", "gates"),
}


def _load(path: pathlib.Path) -> dict:
    """Parse one declaration artifact, or fail loudly naming the file."""
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    for required in ("semver", "class_id", "declaration"):
        if required not in document:
            raise SystemExit(f"{path.name}: missing required key {required!r}")
    return document


def _render(name: str, document: dict, fields: tuple[str, ...]) -> list[str]:
    """One block per artifact: what it is, and the fields a gate reads back."""
    declaration = document["declaration"]
    lines = [
        f"  {name}",
        f"    class_id   {document['class_id']}  v{document['semver']}",
    ]
    for field in fields:
        value = declaration.get(field, "<ABSENT>")
        if isinstance(value, dict):
            rendered = f"{len(value)} entries: {', '.join(sorted(map(str, value)))}"
        elif isinstance(value, list):
            rendered = f"{len(value)} entries" if len(value) > 6 else str(value)
        else:
            rendered = repr(value)
        if len(rendered) > 96:
            rendered = rendered[:93] + "..."
        lines.append(f"    {field:<26s} {rendered}")
    return lines


def main() -> int:
    print("cp-04 corporate-family-tree — ARTIFACT LOAD ONLY (Gate 2, wave 3)")
    print(f"artifacts: {ARTIFACTS}")
    print()

    loaded: dict[str, dict] = {}
    for name, fields in _EXPECTED.items():
        path = ARTIFACTS / name
        if not path.is_file():
            print(f"  {name}: MISSING", file=sys.stderr)
            return 1
        document = _load(path)
        loaded[name] = document
        print("\n".join(_render(name, document, fields)))
        print()

    gates = loaded["gates.yaml"]["declaration"]["gates"]
    unsabotaged = [gate["id"] for gate in gates if gate["observed_red"] is None]
    print(f"declared product gates: {len(gates)}")
    print(f"  never yet observed RED: {len(unsabotaged)} — {', '.join(unsabotaged)}")
    print("  a gate that has never been seen red is not evidence that it runs.")
    print()

    steps = loaded["assembly-recipe.yaml"]["declaration"]["steps"]
    with_operator = [step for step in steps if step["operator"] is not None]
    print(f"recipe steps: {len(steps)}, of which {len(with_operator)} declare an operator")
    print("  and exactly 2 of those are registered operators that enter lineage.")
    print()

    # The canonical encoder refuses a float. Running the whole loaded set
    # through it is what turns "keep the decimal quoted" from a convention
    # into something that fails at the first run after it is broken.
    digest = content_hash(loaded)
    print(f"canonical digest of the artifact set: {digest}")
    print()
    print("Nothing was assembled and no store was opened. The deployment arrives")
    print("at plan 24.4-06 and the assembly at plan 24.4-07.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
