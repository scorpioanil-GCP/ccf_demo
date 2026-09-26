"""D-IMPL-357 B4 — measure the null-attribute population before choosing to
omit a ``None`` attribute in ``SpecDrivenEntityResolution.resolve``.

**Read-only.** This tool changes nothing; it only measures and prints. B4's
ruling ("omit a `None` attribute, after measuring the null-attribute
population") is conditioned on the measurement, so the measurement has to
exist and be inspectable *before* the one-line behavior change lands (CLAUDE.md
§9's "examples are probes, not repair targets" discipline extends the same
posture here: measure first, then commit to the smallest change the
measurement supports).

Two independent measurements, per the brief (`task-B2-brief.md` Step 1):

1. **Fixture rows carrying a literal ``null`` under a declared attribute-key
   name.** Today, ``attributes={key: str(payload[key]) for key in
   rule.attribute_keys if key in payload}`` stores such a row's attribute as
   the *string* ``"None"``. If any committed fixture row already has this
   shape, the B4 change (omitting the key instead) would change what a test
   observes for that row — so this has to be checked, not assumed, before the
   one-line change is made.

   Two independent inputs are combined:

   - **Which attribute-key names are declared at all**, by loading every
     ``*.yaml`` under ``tests/fixtures/`` and collecting every
     ``attribute_keys`` list found under any mapping that also carries an
     ``entity_class`` key — this matches both the plural
     ``entity_rules: [...]`` shape (``EntityResolutionSpec``'s on-disk form,
     e.g. ``tests/fixtures/banking/ontology.yaml``) and the singular
     ``entity_rule: {...}`` shape used at the A2A admission seam
     (``tests/fixtures/banking/a2a.yaml``), without needing two code paths.
   - **Which fixture rows carry a JSON/YAML ``null`` under one of those
     names**, by walking every JSON value (recursively, since a CDC fixture
     row nests the actual field-bearing record under ``"after"``/``"before"``)
     in every ``tests/fixtures/**/*.jsonl`` line and every
     ``tests/signal_layer/fixtures/*.json`` document — the two data-row
     fixture formats a payload reaching ``SpecDrivenEntityResolution.resolve``
     is drawn from in this tree.

2. **``or ""`` coercion sites already present in ``examples/**/*.py``** — code
   that pre-empts today's ``"None"``-string behavior by coercing a null
   attribute value to ``""`` before it ever reaches an attribute dict. A
   nonzero population here means examples already work around the defect B4
   fixes; the exact grep is reproduced from the D-IMPL-357 security-remediation
   design recon (`docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md:346`)
   so this script's count can be checked against that entry:

       grep -rn 'or ""' --include='*.py' examples

   The recon recorded 95 sites in 32 files across 21 example trees; this
   script reproduces that grep exactly (via ``subprocess``, not a
   re-implementation in Python) so a re-run can never silently drift from the
   citable number by an implementation difference in "what counts as a site".

Usage::

    PYTHONPATH=src:runtime .venv/bin/python -m tools.measure_null_attributes

Nothing is written to the tree; redirect stdout to capture the report, e.g.

    PYTHONPATH=src:runtime .venv/bin/python -m tools.measure_null_attributes \\
        > .superpowers/sdd/2026-09-25-v1-0-2-wave-1-opening-sheet/evidence/357-B4-null-attributes.txt
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Every yaml file that might declare an entity-resolution rule's
#: ``attribute_keys`` (brief: ``tests/fixtures/**/*.yaml``).
ATTRIBUTE_SPEC_GLOB = "tests/fixtures/**/*.yaml"

#: Fixture row sources a payload reaching ``SpecDrivenEntityResolution`` is
#: drawn from in this tree (brief: exactly these two globs).
JSONL_GLOB = "tests/fixtures/**/*.jsonl"
JSON_GLOB = "tests/signal_layer/fixtures/*.json"

#: The exact recon grep (security-remediation design, B4 row), reproduced
#: verbatim so this tool's count is checkable against that citable number.
OR_EMPTY_GREP = ("grep", "-rn", 'or ""', "--include=*.py", "examples")


def declared_attribute_keys() -> dict[str, list[str]]:
    """Every ``attribute_keys`` name declared anywhere under ``tests/fixtures/``.

    Maps each declared attribute-key name to the sorted list of repo-relative
    yaml files that declare it. Walks the whole parsed document rather than
    special-casing ``entity_rules`` vs. ``entity_rule`` — any mapping that
    carries both ``entity_class`` and ``attribute_keys`` is treated as a rule,
    which is exactly the ``EntityResolutionRule`` shape regardless of whether
    it sits under the plural or singular key.
    """
    declared: dict[str, list[str]] = {}
    for path in sorted(REPO_ROOT.glob(ATTRIBUTE_SPEC_GLOB)):
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            print(f"  ! could not parse {path} as yaml: {exc}", file=sys.stderr)
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        for rule in _iter_rule_like_mappings(document):
            for key in rule.get("attribute_keys") or ():
                declared.setdefault(key, []).append(rel)
    return {key: sorted(set(files)) for key, files in declared.items()}


def _iter_rule_like_mappings(node: Any) -> list[dict[str, Any]]:
    """Every mapping anywhere in ``node`` that carries both ``entity_class``
    and ``attribute_keys`` — the shape common to ``EntityResolutionRule``'s
    on-disk form under either its plural or singular parent key."""
    found: list[dict[str, Any]] = []

    def _walk(value: Any) -> None:
        if isinstance(value, dict):
            if "entity_class" in value and "attribute_keys" in value:
                found.append(value)
            for child in value.values():
                _walk(child)
        elif isinstance(value, list):
            for item in value:
                _walk(item)

    _walk(node)
    return found


def _iter_json_pairs(node: Any, path: str) -> list[tuple[str, str, Any]]:
    """Every ``(container_path, key, value)`` triple anywhere in ``node``."""
    pairs: list[tuple[str, str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            pairs.append((path, key, value))
            pairs.extend(_iter_json_pairs(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            pairs.extend(_iter_json_pairs(item, f"{path}[{index}]"))
    return pairs


def null_attribute_hits(declared: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    """Every ``(fixture_file, json_path, key)`` where a declared attribute-key
    name carries a literal ``null`` in a fixture row.

    Reads every ``.jsonl`` line and every ``.json`` document under the two
    fixture globs and walks each parsed structure recursively (a CDC event's
    field-bearing record sits under ``"after"``/``"before"``, not at the
    row's top level), so a match under any nesting depth is found.
    """
    hits: list[tuple[str, str, str]] = []

    for path in sorted(REPO_ROOT.glob(JSONL_GLOB)):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            for json_path, key, value in _iter_json_pairs(row, f"line {line_no}"):
                if key in declared and value is None:
                    hits.append((rel, json_path, key))

    for path in sorted(REPO_ROOT.glob(JSON_GLOB)):
        rel = path.relative_to(REPO_ROOT).as_posix()
        document = json.loads(path.read_text(encoding="utf-8"))
        for json_path, key, value in _iter_json_pairs(document, "$"):
            if key in declared and value is None:
                hits.append((rel, json_path, key))

    return hits


def or_empty_sites() -> tuple[int, int, int, str]:
    """Reproduce the recon's exact grep for ``or ""`` sites under ``examples/``.

    Returns ``(sites, files, trees, raw_output)`` — ``trees`` counts distinct
    top-level directories under ``examples/`` that own at least one match, the
    unit the recon reported ("32 files across 21 trees").
    """
    result = subprocess.run(
        OR_EMPTY_GREP, cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    # grep exits 1 when it finds nothing to match, which is a normal outcome
    # here, not a tool failure — only 2+ (a real grep error) is treated as one.
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"{' '.join(OR_EMPTY_GREP)} failed (exit {result.returncode}): {result.stderr}"
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    files = sorted({line.split(":", 1)[0] for line in lines})
    trees = sorted(
        {
            pathlib.PurePosixPath(f).parts[1]
            for f in files
            if len(pathlib.PurePosixPath(f).parts) > 1
        }
    )
    return len(lines), len(files), len(trees), result.stdout


def main() -> int:
    print("=" * 78)
    print("D-IMPL-357 B4 — null-attribute population measurement (read-only)")
    print("=" * 78)

    print()
    print("--- 1. Declared attribute_keys names, by yaml file ---")
    declared = declared_attribute_keys()
    if not declared:
        print("  (none declared under tests/fixtures/**/*.yaml)")
    for key, spec_files in sorted(declared.items()):
        print(f"  {key!r}: {', '.join(spec_files)}")
    print(f"  total distinct attribute-key names declared: {len(declared)}")

    print()
    print("--- 2. Fixture rows carrying a null under a declared attribute key ---")
    print(f"  scanned: {JSONL_GLOB}, {JSON_GLOB}")
    hits = null_attribute_hits(declared)
    if not hits:
        print("  NONE FOUND — 0 fixture rows carry a null under a declared "
              "attribute-key name.")
    else:
        print(f"  {len(hits)} HIT(S):")
        for fixture_file, json_path, key in hits:
            print(f"    {fixture_file}: {json_path}.{key} = null")
    print(f"  population size: {len(hits)}")

    print()
    print("--- 3. `or \"\"` coercion sites under examples/**/*.py ---")
    print(f"  grep: {' '.join(OR_EMPTY_GREP)}")
    site_count, file_count, tree_count, raw = or_empty_sites()
    print(raw, end="" if raw.endswith("\n") or not raw else "\n")
    print(f"  sites: {site_count}, files: {file_count}, trees: {tree_count}")
    print(
        "  recon expectation (security-remediation design, B4 row): "
        "95 sites, 32 files, 21 trees"
    )
    if (site_count, file_count, tree_count) == (95, 32, 21):
        print("  MATCHES the recon expectation exactly.")
    else:
        print(
            "  DOES NOT MATCH the recon expectation — report this discrepancy,"
            " do not silently trust either number."
        )

    print()
    print("=" * 78)
    print("Summary")
    print("=" * 78)
    print(f"  fixture nulls on declared attribute keys : {len(hits)}")
    print(f"  pre-existing `or \"\"` workaround sites    : {site_count} ({file_count} files, {tree_count} trees)")
    print(
        "  implication: the measured fixture population is"
        f" {'EMPTY' if not hits else 'NONEMPTY'} — omitting a null attribute"
        f" {'changes no committed fixture assertion' if not hits else 'may change committed fixture assertions; inspect the hits above before proceeding'}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
