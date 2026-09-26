"""D-IMPL-357 B4 — measure the null-attribute population before choosing to
omit a ``None`` attribute in ``SpecDrivenEntityResolution.resolve``.

**Read-only.** This tool changes nothing; it only measures and prints. B4's
ruling ("omit a `None` attribute, after measuring the null-attribute
population") is conditioned on the measurement, so the measurement has to
exist and be inspectable *before* the one-line behavior change lands (CLAUDE.md
§9's "examples are probes, not repair targets" discipline extends the same
posture here: measure first, then commit to the smallest change the
measurement supports).

Why this tool prints denominators
---------------------------------

The first revision of this tool printed ``NONE FOUND — 0 fixture rows carry a
null`` and nothing else: no scanned-file list, no row count, no count of nulls
under *any* key. Review measured the scanned population and found the printed
zero was **structurally guaranteed** — the two files the globs reached contain
no null under any key at all, so the run never demonstrated the matcher could
fire, and a fixture rename would have produced byte-identical output at exit 0.

That is this project's own standing rule firing (CLAUDE.md §3.1): *absence of a
failure signal is not presence of a success signal*, and a count without its
population is not a measurement. Three consequences, all structural here:

1. **Every scan prints its denominators** — which files were opened, how many
   rows they held, and how many key/value pairs the null test actually
   examined.
2. **Every scan prints the null count under ANY key**, not only under a
   declared attribute key. That second number is the *don't-know
   discriminator*: a declared-key count of zero beside an any-key count of zero
   means "the scan saw no nulls at all, so it proves nothing about declared
   keys"; a declared-key zero beside a large any-key count means the matcher
   was live and the declared keys genuinely have no nulls.
3. **The run carries its own positive control.** ``positive_control()`` drives
   the same matchers over synthetic rows whose answer is known, and the report
   prints whether each fired. A glob that matches no files, an empty declared
   set, or a failed control makes the tool exit **non-zero** — the zero-exit
   silence that made the first run unreadable is gone.

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
     ``tests/signal_layer/fixtures/*.json`` document.

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

What the null test reports, and what the SDK does — deliberately different
--------------------------------------------------------------------------

``null_reason`` reports a ``None``, **and also** a non-finite ``float`` or
``Decimal`` (NaN, ±Infinity), as null-like. The mint site in
``src/ccf/assembly/worker.py`` tests only ``is not None`` and therefore stores
a non-finite value as its text. That asymmetry is intentional and is not this
tool papering over it: reporting a population is measurement, and widening the
SDK's check would be a behavior change nobody has ruled. A non-finite attribute
value is a **held question** for the decision owner, and the owner can only
rule on a population they can see — which is why this tool counts it and says
so rather than passing silently over it.

Usage::

    PYTHONPATH=src:runtime .venv/bin/python -m tools.measure_null_attributes

Nothing is written to the tree; redirect stdout to capture the report, e.g.

    PYTHONPATH=src:runtime .venv/bin/python -m tools.measure_null_attributes \\
        > .superpowers/sdd/2026-09-25-v1-0-2-wave-1-opening-sheet/evidence/357-B4-null-attributes.txt

Exit code: ``0`` when every glob matched at least one file, the declared set is
non-empty, and every positive control fired. Non-zero otherwise — including
when the report's numbers are fine but the instrument could not be shown
working, because that is the *don't-know* state and it is not a pass.
"""

from __future__ import annotations

import json
import math
import pathlib
import subprocess
import sys
from decimal import Decimal
from typing import Any, NamedTuple

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Every yaml file that might declare an entity-resolution rule's
#: ``attribute_keys`` (brief: ``tests/fixtures/**/*.yaml``).
ATTRIBUTE_SPEC_GLOB = "tests/fixtures/**/*.yaml"

#: Fixture row sources a payload reaching ``SpecDrivenEntityResolution`` is
#: drawn from in this tree, each paired with the unit its denominator counts.
JSONL_GLOB = "tests/fixtures/**/*.jsonl"
JSON_GLOB = "tests/signal_layer/fixtures/*.json"

#: The exact recon grep (security-remediation design, B4 row), reproduced
#: verbatim so this tool's count is checkable against that citable number.
OR_EMPTY_GREP = ("grep", "-rn", 'or ""', "--include=*.py", "examples")


class Hit(NamedTuple):
    """One fixture value that is null-like under a *declared* attribute key."""

    source: str
    locator: str
    key: str
    reason: str


class ScanStat(NamedTuple):
    """The denominator for one scanned file — what the null test actually saw.

    ``pairs`` is the real denominator of the null test: the number of
    key/value pairs it examined. ``null_any`` is the don't-know discriminator
    described in the module docstring.
    """

    source: str
    unit: str
    units: int
    pairs: int
    null_any: int
    hits: int


def null_reason(value: Any) -> str | None:
    """``"null"``, ``"non-finite"``, or ``None`` if the value is a real value.

    Reports more than the SDK's mint site tests for, on purpose — see the
    module docstring's note on the deliberate asymmetry.
    """
    if value is None:
        return "null"
    if isinstance(value, float) and not math.isfinite(value):
        return "non-finite"
    if isinstance(value, Decimal) and not value.is_finite():
        return "non-finite"
    return None


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


def _count_mappings(node: Any) -> int:
    """Every mapping anywhere in ``node``, the root and list members included.

    A ``.json`` fixture here may be a top-level *list* of row objects
    (``tests/signal_layer/fixtures/cp05-exposure-acquisition.json`` is 177 of
    them), so counting only the dicts that sit under a key reports 0 for a file
    holding 177 rows — a denominator that lies in the direction of "nothing was
    scanned" is worse than none.
    """
    if isinstance(node, dict):
        return 1 + sum(_count_mappings(value) for value in node.values())
    if isinstance(node, list):
        return sum(_count_mappings(item) for item in node)
    return 0


def _scan_json_structure(
    *,
    declared: set[str],
    node: Any,
    locator_root: str,
    source: str,
) -> tuple[list[Hit], int, int]:
    """Return ``(hits, pairs_examined, null_like_under_any_key)``."""
    hits: list[Hit] = []
    pairs = 0
    null_any = 0
    for json_path, key, value in _iter_json_pairs(node, locator_root):
        pairs += 1
        reason = null_reason(value)
        if reason is None:
            continue
        null_any += 1
        if key in declared:
            hits.append(Hit(source=source, locator=f"{json_path}.{key}", key=key, reason=reason))
    return hits, pairs, null_any


def scan_jsonl(*, path: pathlib.Path, declared: set[str]) -> tuple[list[Hit], ScanStat]:
    """Scan one ``.jsonl`` fixture — one row per non-blank line."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    hits: list[Hit] = []
    rows = pairs = null_any = 0
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        rows += 1
        row_hits, row_pairs, row_nulls = _scan_json_structure(
            declared=declared, node=json.loads(line), locator_root=f"line {line_no}", source=rel
        )
        hits.extend(row_hits)
        pairs += row_pairs
        null_any += row_nulls
    return hits, ScanStat(
        source=rel, unit="jsonl rows", units=rows, pairs=pairs, null_any=null_any, hits=len(hits)
    )


def scan_json(*, path: pathlib.Path, declared: set[str]) -> tuple[list[Hit], ScanStat]:
    """Scan one ``.json`` fixture document."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    document = json.loads(path.read_text(encoding="utf-8"))
    hits, pairs, null_any = _scan_json_structure(
        declared=declared, node=document, locator_root="$", source=rel
    )
    return hits, ScanStat(
        source=rel,
        unit="json mappings",
        units=_count_mappings(document),
        pairs=pairs,
        null_any=null_any,
        hits=len(hits),
    )


def scan_rows(declared: set[str]) -> tuple[list[Hit], list[ScanStat], list[str]]:
    """Scan every row fixture. Returns ``(hits, per-file stats, empty globs)``."""
    hits: list[Hit] = []
    stats: list[ScanStat] = []
    empty: list[str] = []

    for glob, reader in ((JSONL_GLOB, scan_jsonl), (JSON_GLOB, scan_json)):
        matched = sorted(REPO_ROOT.glob(glob))
        if not matched:
            empty.append(glob)
        for path in matched:
            file_hits, stat = reader(path=path, declared=declared)
            hits.extend(file_hits)
            stats.append(stat)

    return hits, stats, empty


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


def positive_control() -> list[tuple[str, bool, str]]:
    """Drive the matchers over synthetic inputs whose answer is known.

    Returns ``(what_was_driven, fired_as_expected, observed)`` per control. A
    report that cannot show its own matcher firing cannot distinguish "nothing
    is there" from "nothing was looked at", which is the exact failure this
    tool was sent back to fix.
    """
    controls: list[tuple[str, bool, str]] = []

    nested = {"op": "u", "after": {"jurisdiction": None, "deeper": {"currency": float("nan")}}}
    hits, pairs, null_any = _scan_json_structure(
        declared={"jurisdiction", "currency"},
        node=nested,
        locator_root="synthetic",
        source="<positive control>",
    )
    controls.append(
        (
            "nested JSON row, null under a declared key at depth 2",
            [h.key for h in hits] == ["jurisdiction", "currency"],
            f"{len(hits)} hit(s) {[h.key + '=' + h.reason for h in hits]}"
            f" over {pairs} pairs, {null_any} null-like under any key",
        )
    )

    clean = {"after": {"jurisdiction": "IE", "currency": "USD"}}
    clean_hits, _, clean_nulls = _scan_json_structure(
        declared={"jurisdiction", "currency"},
        node=clean,
        locator_root="synthetic",
        source="<negative control>",
    )
    controls.append(
        (
            "NEGATIVE control: same keys, real values — must NOT fire",
            not clean_hits and clean_nulls == 0,
            f"{len(clean_hits)} hit(s), {clean_nulls} null-like",
        )
    )

    controls.append(
        (
            "undeclared key carrying a null — must NOT fire",
            not _scan_json_structure(
                declared={"jurisdiction"},
                node={"something_else": None},
                locator_root="synthetic",
                source="<negative control>",
            )[0],
            "no hit",
        )
    )

    reasons = [
        null_reason(None),
        null_reason(float("nan")),
        null_reason(float("inf")),
        null_reason(Decimal("NaN")),
        null_reason(Decimal("-Infinity")),
        null_reason(""),
        null_reason("None"),
        null_reason(0),
    ]
    controls.append(
        (
            "null_reason over None / NaN / Inf / Decimal NaN / Decimal -Inf / '' / 'None' / 0",
            reasons
            == ["null", "non-finite", "non-finite", "non-finite", "non-finite", None, None, None],
            str(reasons),
        )
    )

    return controls


def main() -> int:
    exit_code = 0
    print("=" * 78)
    print("D-IMPL-357 B4 — null-attribute population measurement (read-only)")
    print("=" * 78)

    print()
    print("--- 0. Positive control: can the matcher fire at all? ---")
    for what, fired, observed in positive_control():
        print(f"  [{'FIRED' if fired else 'FAILED'}] {what}")
        print(f"            observed: {observed}")
        if not fired:
            exit_code = 1

    print()
    print("--- 1. Declared attribute_keys names, by yaml file ---")
    print(f"  scanned glob: {ATTRIBUTE_SPEC_GLOB}")
    spec_files = sorted(REPO_ROOT.glob(ATTRIBUTE_SPEC_GLOB))
    print(f"  spec files matched: {len(spec_files)}")
    for path in spec_files:
        print(f"    {path.relative_to(REPO_ROOT).as_posix()}")
    declared = declared_attribute_keys()
    if not declared:
        print("  (none declared — the scan below cannot say anything; failing)")
        exit_code = 1
    for key, sources in sorted(declared.items()):
        print(f"  {key!r}: {', '.join(sources)}")
    print(f"  total distinct attribute-key names declared: {len(declared)}")

    print()
    print("--- 2. Fixture rows carrying a null under a declared attribute key ---")
    hits, stats, empty_globs = scan_rows(set(declared))
    print(f"  globs: {JSONL_GLOB}, {JSON_GLOB}")
    for glob in empty_globs:
        print(f"  ! GLOB MATCHED NO FILES: {glob} — the scan below is empty by "
              "construction, not by measurement")
        exit_code = 1
    print("  scanned (the denominators):")
    for stat in stats:
        print(
            f"    {stat.source}: {stat.units} {stat.unit}, {stat.pairs} key/value pairs"
            f" examined, {stat.null_any} null-like under ANY key, {stat.hits} under a"
            " declared key"
        )
    total_units = sum(stat.units for stat in stats)
    total_pairs = sum(stat.pairs for stat in stats)
    total_null_any = sum(stat.null_any for stat in stats)
    print(
        f"  totals: {len(stats)} files, {total_units} rows/mappings,"
        f" {total_pairs} key/value pairs examined"
    )
    print(f"  null-like values under ANY key (the don't-know discriminator): {total_null_any}")
    if hits:
        print(f"  {len(hits)} HIT(S) under a declared attribute key:")
        for hit in hits:
            print(f"    {hit.source}: {hit.locator} = {hit.reason}")
    else:
        print("  0 hits under a declared attribute key.")
    print(f"  population size: {len(hits)}")
    if not hits and total_null_any == 0:
        print(
            "  READ THIS AS DON'T-KNOW, NOT AS CLEAN: the scanned files carry no"
            " null-like value under ANY key, so this zero is a fact about the"
            " scan's reach, not about declared attribute keys."
        )

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
        exit_code = 1
    print(
        "  WHAT THIS POPULATION IS, AND IS NOT: each site coerces a null to `\"\"`"
        " in the payload builder, BEFORE the attribute comprehension sees it. The"
        " B4 change therefore cannot alter any of them — they are a RESIDUAL, not"
        " a population B4 clears. Each one stores an answered empty string that"
        " PolicyFilter._admits and every completeness term read as a present"
        " value: the same defect class B4 closes, relocated one step upstream."
        " That is a gap-ledger row, not an example fix (examples/ is frozen under"
        " D-IMPL-261)."
    )

    print()
    print("=" * 78)
    print("Summary")
    print("=" * 78)
    print(f"  files scanned for rows                   : {len(stats)}")
    print(f"  key/value pairs examined                 : {total_pairs}")
    print(f"  null-like under ANY key                  : {total_null_any}")
    print(f"  null-like under a DECLARED attribute key : {len(hits)}")
    print(f"  residual `or \"\"` sites upstream          : {site_count} ({file_count} files, {tree_count} trees)")
    print(f"  exit code                                : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
