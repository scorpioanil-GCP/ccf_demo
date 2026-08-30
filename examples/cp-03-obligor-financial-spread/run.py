"""The client — **Gate 2 in progress; this driver LOADS the artifacts and stops.**

[ADAPT] all of it. [MECHANISM] nothing.

**WHAT THIS FILE IS RIGHT NOW, STATED PLAINLY SO NOBODY MISTAKES IT FOR THE
DRIVER.** Phase 24.3 builds this example in the order its specification fixes:
specification, then artifacts, then the census harness, then the assembly, then
the gates, then the documentation. The artifacts are written and the assembly is
NOT. This file exists at this point for one reason: the repository's own gate
(`tests/examples/test_artifact_schema_headers.py::test_every_covered_artifact_directory_sits_under_an_example_root`)
holds that an `artifacts/` directory beside no `run.py` is not an example, and
that predicate is deliberate and load-bearing rather than an obstacle to route
around. A red tree carried across a session is worse than a thin driver, so the
driver is thin and says so.

**WHAT IT DELIBERATELY DOES NOT DO** — bounds set by Dave, 2026-08-29:

* it does not assemble anything,
* it does not open Postgres or any other store,
* it does not preview `produce.py`, which is not written and must not be
  sketched here, because a sketch is a design decision taken in the wrong file.

It reads the four declaration artifacts and prints enough to prove each one
parsed: its path, the values a later gate will read back out of it, and the size
of the vocabulary it declares. That is the whole contract of this file until
step 3 replaces it.

**THE QUOTED DECIMALS ARE NOT A TYPO, AND THIS FILE ENFORCES THEM.**
`material_threshold` and `debt_tolerance` are quoted in their YAML and print
here exactly as they parse — as text, not floats. A Control Plane artifact
refuses a float because a float is not bit-stable across platforms, and a value
that is not bit-stable cannot be replayed.

That rule is not merely asserted here. Every loaded artifact is put through
`ccf.contracts.canonical::content_hash`, the fabric's own canonical encoder,
which **raises on a float**. So unquoting either decimal does not produce a
subtly different number that survives review — it stops this driver with a
`CanonicalizationError` naming the offending value. The digest it returns is
also a stable fingerprint of the artifact set, which is what a later step will
pin a replay against.
"""

from __future__ import annotations

import pathlib
import sys

import yaml

from ccf.contracts.canonical import content_hash

ARTIFACTS = pathlib.Path(__file__).resolve().parent / "artifacts"

#: The four declaration artifacts, and the fields a reader should see proved.
#: Names only — every VALUE lives in the YAML, which is the point of the split.
_EXPECTED: dict[str, tuple[str, ...]] = {
    "restatement.yaml": ("fact_identity_key", "material_threshold", "detected_by"),
    "ttl.yaml": ("declared_ttl_seconds", "ttl_anchor_basis"),
    "spread-lines.yaml": ("tag_map", "ratios", "adjustments"),
    "question.yaml": ("subject", "asked_at", "parameters"),
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
    lines = [f"  {name}", f"    class_id   {document['class_id']}  v{document['semver']}"]
    for field in fields:
        value = declaration.get(field, "<ABSENT>")
        if isinstance(value, dict):
            rendered = f"{len(value)} entries: {', '.join(sorted(value))}"
        elif isinstance(value, list):
            rendered = f"{len(value)} entries" if len(value) > 6 else str(value)
        else:
            rendered = repr(value)
        lines.append(f"    {field:<22s} {rendered}")
    return lines


def main() -> int:
    print("cp-03 obligor-financial-spread — ARTIFACT LOAD ONLY (Gate 2 step 1)")
    print(f"artifacts: {ARTIFACTS}")
    print()

    tags: set[str] = set()
    for name, fields in _EXPECTED.items():
        path = ARTIFACTS / name
        if not path.is_file():
            print(f"  {name}: MISSING", file=sys.stderr)
            return 1
        document = _load(path)
        print("\n".join(_render(name, document, fields)))
        print()
        if name == "spread-lines.yaml":
            for line in document["declaration"]["tag_map"].values():
                tags.update(line["tags"])

    print(f"US-GAAP tags mapped to a spread line: {len(tags)}")

    # The canonical encoder refuses a float. Running the whole loaded set
    # through it is what turns "keep the decimals quoted" from a convention
    # into something that fails at the first run after it is broken.
    digest = content_hash({name: _load(ARTIFACTS / name) for name in _EXPECTED})
    print(f"canonical digest of the artifact set: {digest}")
    print()
    print("Nothing was assembled and no store was opened. The assembly arrives")
    print("at step 3 of Phase 24.3; the census harness is step 2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
