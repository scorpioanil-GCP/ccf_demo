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
A reviewer then opened a *third* committed row format the globs never reached
and found real nulls under real declared attribute keys.

That is this project's own standing rule firing (CLAUDE.md §3.1): *absence of a
failure signal is not presence of a success signal*, and a count without its
population is not a measurement. Four consequences, all structural here:

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
   set, an unparsable row, or a failed control makes the tool exit **non-zero**
   — the zero-exit silence that made the first run unreadable is gone.
4. **The scanned population is the one the ruling conditions on**, not the
   subset that was convenient to read — see the next section.

The three committed row formats, and the two declaration populations
--------------------------------------------------------------------

**Rows.** A payload reaching ``SpecDrivenEntityResolution.resolve`` is drawn
from three committed formats in this tree, and the first revision opened only
two of them:

- ``tests/fixtures/**/*.jsonl`` — CDC event rows, field-bearing record nested
  under ``"after"``/``"before"``.
- ``tests/signal_layer/fixtures/*.json`` — an acquisition document, a top-level
  *list* of row objects.
- ``tests/examples/fixtures/*.sql`` — **SQL seed rows**, the format the first
  revision missed entirely. Values are positional, so each row tuple is matched
  against its ``INSERT`` statement's own column list. This is where the nulls
  are: ``tests/examples/fixtures/cp_02_facility_rows.sql`` carries a bare
  ``null`` under the column ``maturity_date`` on seven row tuples and under
  ``commitment_amount`` on one, and both names are declared attribute keys in
  cp-02's ``ccf_config.yaml``.

**Declarations.** ``attribute_keys`` is declared in more places than
``tests/fixtures/`` — 13 names live there, and hundreds more live in example
``ccf_config.yaml`` files, in spec fixtures elsewhere under ``tests/``, and
inline in Python test modules. All three are read, and each source's own name
set is printed separately so a reader can see which declaration a hit came
from rather than a merged blur.

Because the merged name set is a **union across unrelated products**, a hit
against it is an upper bound: a name declared by one example's rule may be
null in a different example's fixture, and the two never meet at runtime. So
the report prints both numbers — the tree-wide union (upper bound) and a
**product-scoped** pairing that matches each ``cp_NN_*.sql`` fixture only
against the ``examples/cp-NN-*/ccf_config.yaml`` rules that actually consume
it. The scoped number is the precise one; the union number is the ceiling.

A second measurement: the ``or ""`` residual
--------------------------------------------

``or ""`` coercion sites already present in ``examples/**/*.py`` — code that
pre-empts today's ``"None"``-string behavior by coercing a null attribute value
to ``""`` before it ever reaches an attribute dict. The exact grep is
reproduced from the D-IMPL-357 security-remediation design recon
(`docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md:346`)
so this script's count can be checked against that entry:

    grep -rn 'or ""' --include='*.py' examples

The recon recorded 95 sites in 32 files across 21 example trees; this script
reproduces that grep exactly (via ``subprocess``, not a re-implementation in
Python) so a re-run can never silently drift from the citable number by an
implementation difference in "what counts as a site".

**What that population is NOT.** Every one of those sites coerces the null in
the payload builder, *upstream* of the attribute comprehension — so the B4
change cannot alter a single one of them. They are a **residual**, not a
population B4 clears: each stores an answered empty string that
``PolicyFilter._admits`` and every completeness term read as a present value,
which is the same defect class B4 closes, relocated one step upstream. Reading
them as cleared is the error this paragraph exists to prevent. The same is true
of the ``str(...)`` sites the builder scan below counts: ``str(None)`` is
``"None"`` in the example's own code, before the fabric sees it.

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
non-empty, every row parsed cleanly, and every positive control fired.
Non-zero otherwise — including when the report's numbers are fine but the
instrument could not be shown working, because that is the *don't-know* state
and it is not a pass.
"""

from __future__ import annotations

import ast
import bisect
import collections
import functools
import json
import math
import pathlib
import re
import subprocess
import sys
from decimal import Decimal
from typing import Any, Iterator, NamedTuple

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Where ``attribute_keys`` is declared on disk. Every one of these is read;
#: each file's own name set is printed separately in section 1.
#:
#: Grouped, because the two suffix spellings of one format are **one source**.
#: A group that matches nothing is a hole and fails the run; an individual
#: alternative spelling that matches nothing is not — measured, this tree has
#: no ``.yml`` under ``tests/`` at all, and reporting that as a missing
#: population would train the reader to ignore the very signal the failing
#: exit exists to carry.
YAML_SPEC_GLOB_GROUPS: tuple[tuple[str, ...], ...] = (
    ("tests/**/*.yaml", "tests/**/*.yml"),
    ("examples/**/ccf_config.yaml",),
)

#: ``attribute_keys`` declared inline in Python, read from the AST so a
#: computed declaration is *reported as unreadable* rather than silently
#: dropped.
PYTHON_SPEC_GLOB = "tests/**/*.py"

#: The three committed row formats a payload reaching
#: ``SpecDrivenEntityResolution`` is drawn from in this tree.
JSONL_GLOB = "tests/fixtures/**/*.jsonl"
JSON_GLOB = "tests/signal_layer/fixtures/*.json"
SQL_GLOB = "tests/examples/fixtures/*.sql"

#: Example payload builders — scanned for dict literals that hand a declared
#: attribute key a value that is, or can be, ``None``.
EXAMPLE_BUILDER_GLOB = "examples/**/*.py"

#: The exact recon grep (security-remediation design, B4 row), reproduced
#: verbatim so this tool's count is checkable against that citable number.
OR_EMPTY_GREP = ("grep", "-rn", 'or ""', "--include=*.py", "examples")

#: How many individual line numbers to print per aggregated (file, key) group
#: before eliding. The count is always printed in full; only the line list is
#: capped, and never below the size of the groups this round's finding names.
LINES_PER_GROUP = 12


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
    described in the module docstring. ``unmatched`` counts values the scan
    could not name a column for (a SQL ``INSERT`` with no column list, or an
    arity mismatch between the column list and a row tuple) — a row the walker
    cannot read is not a row it has cleared.
    """

    source: str
    unit: str
    units: int
    pairs: int
    null_any: int
    hits: int
    unmatched: int = 0
    error: str = ""


class Declarations(NamedTuple):
    """Every ``attribute_keys`` name on disk, with where each was declared."""

    by_key: dict[str, list[str]]
    by_source: dict[str, list[str]]
    unreadable: list[tuple[str, int]]
    files_per_glob: dict[str, int]
    empty_globs: list[str]

    @property
    def names(self) -> set[str]:
        return set(self.by_key)


class BuilderSite(NamedTuple):
    """One dict-literal site in an example that feeds a declared attribute key."""

    source: str
    line: int
    key: str
    shape: str


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


# --------------------------------------------------------------------------
# Declared attribute-key names
# --------------------------------------------------------------------------


def _iter_rule_like_mappings(node: Any) -> list[dict[str, Any]]:
    """Every mapping anywhere in ``node`` that carries both ``entity_class``
    and ``attribute_keys`` — the shape common to ``EntityResolutionRule``'s
    on-disk form under either its plural or singular parent key.

    Requiring *both* keys is what keeps prose out of the name set: a gate file
    whose ``statement`` mentions ``attribute_keys`` is not a declaration, and
    treating it as one would inflate the denominator with names nothing
    declares.
    """
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


def _literal_str_sequence(node: ast.expr) -> list[str] | None:
    """The list of strings a literal tuple/list/set node holds, else ``None``.

    ``None`` means *not statically readable* — a starred element, a call, a
    comprehension. The caller reports those rather than dropping them, because
    a declaration the tool cannot read is a hole in the denominator.
    """
    if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return None
    names: list[str] = []
    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            names.append(element.value)
        else:
            return None
    return names


def _python_declarations(path: pathlib.Path) -> tuple[list[str], list[int]]:
    """``(names, unreadable_line_numbers)`` declared inline in one Python file.

    Both spellings are read: the keyword argument
    ``attribute_keys=("a", "b")`` and the dict entry
    ``"attribute_keys": ["a", "b"]``.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError) as exc:
        print(f"  ! could not parse {path} as python: {exc}", file=sys.stderr)
        return [], []
    names: list[str] = []
    unreadable: list[int] = []
    for node in ast.walk(tree):
        values: list[ast.expr] = []
        if isinstance(node, ast.keyword) and node.arg == "attribute_keys":
            values.append(node.value)
        elif isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                if (
                    isinstance(key_node, ast.Constant)
                    and key_node.value == "attribute_keys"
                ):
                    values.append(value_node)
        for value in values:
            literal = _literal_str_sequence(value)
            if literal is None:
                unreadable.append(value.lineno)
            else:
                names.extend(literal)
    return names, unreadable


def declared_attribute_keys() -> Declarations:
    """Every ``attribute_keys`` name declared on disk, with its sources.

    Reads the yaml declaration files (``YAML_SPEC_GLOB_GROUPS``) and the inline
    Python declarations (``PYTHON_SPEC_GLOB``). Walks each parsed yaml document
    rather than special-casing ``entity_rules`` vs. ``entity_rule`` — any
    mapping carrying both ``entity_class`` and ``attribute_keys`` is a rule,
    which is exactly the ``EntityResolutionRule`` shape under either parent key.
    """
    by_key: dict[str, list[str]] = {}
    by_source: dict[str, set[str]] = {}
    unreadable: list[tuple[str, int]] = []
    files_per_glob: dict[str, int] = {}
    empty_globs: list[str] = []

    def _record(rel: str, key: str) -> None:
        by_key.setdefault(key, []).append(rel)
        by_source.setdefault(rel, set()).add(key)

    for group in YAML_SPEC_GLOB_GROUPS:
        matched: list[pathlib.Path] = []
        for glob in group:
            found = sorted(REPO_ROOT.glob(glob))
            files_per_glob[glob] = len(found)
            matched.extend(found)
        if not matched:
            empty_globs.append(" | ".join(group))
        for path in sorted(matched):
            try:
                document = yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                print(f"  ! could not parse {path} as yaml: {exc}", file=sys.stderr)
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            for rule in _iter_rule_like_mappings(document):
                for key in rule.get("attribute_keys") or ():
                    _record(rel, key)

    matched_py = sorted(REPO_ROOT.glob(PYTHON_SPEC_GLOB))
    files_per_glob[PYTHON_SPEC_GLOB] = len(matched_py)
    if not matched_py:
        empty_globs.append(PYTHON_SPEC_GLOB)
    for path in matched_py:
        names, unreadable_lines = _python_declarations(path)
        rel = path.relative_to(REPO_ROOT).as_posix()
        for key in names:
            _record(rel, key)
        unreadable.extend((rel, line) for line in unreadable_lines)

    return Declarations(
        by_key={key: sorted(set(files)) for key, files in by_key.items()},
        by_source={rel: sorted(keys) for rel, keys in sorted(by_source.items())},
        unreadable=sorted(unreadable),
        files_per_glob=files_per_glob,
        empty_globs=empty_globs,
    )


def example_tree_declarations() -> dict[str, set[str]]:
    """Each ``examples/<tree>/`` mapped to the attribute keys its rules declare.

    Used for the product-scoped pairing: a ``cp_NN_*.sql`` fixture is matched
    against the ``cp-NN-*`` trees that consume it, so the reported number is
    about rules that actually see those rows.
    """
    per_tree: dict[str, set[str]] = {}
    for path in sorted(REPO_ROOT.glob("examples/**/ccf_config.yaml")):
        tree = path.relative_to(REPO_ROOT).parts[1]
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        names = per_tree.setdefault(tree, set())
        for rule in _iter_rule_like_mappings(document):
            names.update(rule.get("attribute_keys") or ())
    return per_tree


# --------------------------------------------------------------------------
# JSON / JSONL rows
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# SQL seed rows — the third committed row format
# --------------------------------------------------------------------------

_INSERT_RE = re.compile(r"\binsert\s+into\b", re.IGNORECASE)
_VALUES_RE = re.compile(r"\bvalues\b", re.IGNORECASE)
_CAST_RE = re.compile(r"::[A-Za-z_][\w\[\]. ]*$")
_NON_FINITE_TOKENS = frozenset({"nan", "inf", "infinity"})


def _mask_sql(text: str) -> tuple[str, list[bool]]:
    """``(text_with_comments_blanked, in_string_mask)``, same length as input.

    Comments become spaces (newlines kept, so line numbers still work) and
    string literals keep their bytes but are marked, so parenthesis and comma
    scanning can ignore anything inside a quoted value. A JSON literal in a
    ``pricing_grid`` column is full of braces, commas and parentheses; without
    the mask it would tear the row tuple apart.
    """
    out: list[str] = []
    in_string: list[bool] = []
    index = 0
    end = len(text)
    while index < end:
        char = text[index]
        if char == "'":
            out.append(char)
            in_string.append(True)
            index += 1
            while index < end:
                current = text[index]
                if current == "'":
                    # `''` is an escaped quote inside the literal, not its end.
                    if index + 1 < end and text[index + 1] == "'":
                        out.extend(("'", "'"))
                        in_string.extend((True, True))
                        index += 2
                        continue
                    out.append("'")
                    in_string.append(True)
                    index += 1
                    break
                out.append(current)
                in_string.append(True)
                index += 1
            continue
        if char == "-" and index + 1 < end and text[index + 1] == "-":
            while index < end and text[index] != "\n":
                out.append(" ")
                in_string.append(False)
                index += 1
            continue
        if char == "/" and index + 1 < end and text[index + 1] == "*":
            while index < end and not (
                text[index] == "*" and index + 1 < end and text[index + 1] == "/"
            ):
                out.append("\n" if text[index] == "\n" else " ")
                in_string.append(False)
                index += 1
            for _ in range(min(2, end - index)):
                out.append(" ")
                in_string.append(False)
                index += 1
            continue
        out.append(char)
        in_string.append(False)
        index += 1
    return "".join(out), in_string


def _matching_paren(text: str, in_string: list[bool], start: int) -> int:
    """Index just past the ``)`` matching the ``(`` at ``start``."""
    depth = 0
    index = start
    while index < len(text):
        if not in_string[index]:
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
                if depth == 0:
                    return index + 1
        index += 1
    raise ValueError(f"unbalanced parenthesis opened at offset {start}")


def _split_top_level(text: str, in_string: list[bool], start: int, stop: int) -> list[str]:
    """``text[start:stop]`` split on commas that are not nested or quoted."""
    parts: list[str] = []
    depth = 0
    token_start = start
    for index in range(start, stop):
        if in_string[index]:
            continue
        char = text[index]
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[token_start:index])
            token_start = index + 1
    parts.append(text[token_start:stop])
    return parts


def _skip_space(text: str, in_string: list[bool], index: int) -> int:
    while index < len(text) and not in_string[index] and text[index].isspace():
        index += 1
    return index


def sql_insert_rows(text: str) -> Iterator[tuple[list[str], int, list[str]]]:
    """Yield ``(columns, line_number, value_tokens)`` per ``INSERT`` row tuple.

    SQL values are **positional**, so the column list on the ``INSERT`` is the
    only thing that gives a null a name. The column list may sit on its own
    lines and ``values`` on another; row tuples may be separated by comments;
    and a trailing ``on conflict (...) do update`` clause carries a
    parenthesised group that is not a row — so the scan stops at the first
    tuple not preceded by a comma.
    """
    masked, in_string = _mask_sql(text)
    # Newline offsets once, then bisect per row. Counting newlines from the
    # start of the file for each row tuple is O(file × rows) and took 48s on
    # the 7.7MB census fixture alone — a measurement tool nobody will wait for
    # is a measurement tool nobody runs.
    newlines = [index for index, char in enumerate(masked) if char == "\n"]
    for match in _INSERT_RE.finditer(masked):
        if in_string[match.start()]:
            continue
        cursor = match.end()
        values_match = _VALUES_RE.search(masked, cursor)
        paren = masked.find("(", cursor)
        columns: list[str] = []
        if (
            paren != -1
            and not in_string[paren]
            and (values_match is None or paren < values_match.start())
        ):
            close = _matching_paren(masked, in_string, paren)
            columns = [
                token.strip().strip('"').strip()
                for token in _split_top_level(masked, in_string, paren + 1, close - 1)
            ]
            cursor = close
            values_match = _VALUES_RE.search(masked, cursor)
        if values_match is None:
            continue
        cursor = values_match.end()
        while True:
            cursor = _skip_space(masked, in_string, cursor)
            if cursor >= len(masked) or masked[cursor] != "(" or in_string[cursor]:
                break
            close = _matching_paren(masked, in_string, cursor)
            line_number = bisect.bisect_right(newlines, cursor) + 1
            tokens = [
                token.strip()
                for token in _split_top_level(masked, in_string, cursor + 1, close - 1)
            ]
            yield columns, line_number, tokens
            cursor = _skip_space(masked, in_string, close)
            if cursor < len(masked) and masked[cursor] == "," and not in_string[cursor]:
                cursor += 1
                continue
            break


def sql_token_null_reason(token: str) -> str | None:
    """``"null"``, ``"non-finite"``, or ``None`` for one SQL value token.

    A *quoted* ``'null'`` is a real string value and deliberately does not
    match: reading it as a null would be the same error, in the other
    direction, as reading ``str(None)``'s ``"None"`` as an answer.
    """
    stripped = _CAST_RE.sub("", token.strip()).strip()
    lowered = stripped.lower()
    if lowered == "null":
        return "null"
    if len(lowered) >= 2 and lowered[0] == "'" and lowered[-1] == "'":
        core = lowered[1:-1]
    else:
        core = lowered
    if core.lstrip("+-") in _NON_FINITE_TOKENS:
        return "non-finite"
    return None


@functools.lru_cache(maxsize=None)
def _sql_rows_for_path(path: pathlib.Path) -> tuple[tuple[tuple[str, ...], int, tuple[str, ...]], ...]:
    """``sql_insert_rows`` for a file, parsed once.

    Sections 2 and 2b both scan the SQL fixtures — once against the tree-wide
    declared union and once product-scoped — and re-parsing 7.7MB of census
    rows for the second pass buys nothing.
    """
    return tuple(
        (tuple(columns), line, tuple(tokens))
        for columns, line, tokens in sql_insert_rows(path.read_text(encoding="utf-8"))
    )


def scan_sql(*, path: pathlib.Path, declared: set[str]) -> tuple[list[Hit], ScanStat]:
    """Scan one ``.sql`` seed fixture, matching row tuples to column lists."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    hits: list[Hit] = []
    rows = pairs = null_any = unmatched = 0
    error = ""
    try:
        parsed = _sql_rows_for_path(path)
    except ValueError as exc:
        # A statement this walker cannot balance is a file it has NOT cleared.
        # Reported per file and carried into the exit code, rather than raised:
        # one malformed fixture must not abort the other eleven scans, and it
        # must not read as a clean zero either.
        return [], ScanStat(
            source=rel,
            unit="sql insert rows",
            units=0,
            pairs=0,
            null_any=0,
            hits=0,
            error=f"COULD NOT PARSE: {exc}",
        )
    for columns, line_number, tokens in parsed:
        rows += 1
        if len(columns) != len(tokens):
            # Either no column list at all, or the walker mis-split a tuple.
            # Both mean this row's nulls cannot be given a name; counted, and
            # the run exits non-zero rather than reporting a clean scan.
            unmatched += len(tokens)
            continue
        for column, token in zip(columns, tokens):
            pairs += 1
            reason = sql_token_null_reason(token)
            if reason is None:
                continue
            null_any += 1
            if column in declared:
                hits.append(
                    Hit(source=rel, locator=f"line {line_number}", key=column, reason=reason)
                )
    return hits, ScanStat(
        source=rel,
        unit="sql insert rows",
        units=rows,
        pairs=pairs,
        null_any=null_any,
        hits=len(hits),
        unmatched=unmatched,
        error=error,
    )


def scan_rows(declared: set[str]) -> tuple[list[Hit], list[ScanStat], list[str]]:
    """Scan every row fixture. Returns ``(hits, per-file stats, empty globs)``."""
    hits: list[Hit] = []
    stats: list[ScanStat] = []
    empty: list[str] = []

    readers = ((JSONL_GLOB, scan_jsonl), (JSON_GLOB, scan_json), (SQL_GLOB, scan_sql))
    for glob, reader in readers:
        matched = sorted(REPO_ROOT.glob(glob))
        if not matched:
            empty.append(glob)
        for path in matched:
            file_hits, stat = reader(path=path, declared=declared)
            hits.extend(file_hits)
            stats.append(stat)

    return hits, stats, empty


# --------------------------------------------------------------------------
# Example payload builders
# --------------------------------------------------------------------------


def _value_shape(node: ast.expr) -> str:
    """How an example builder hands a value to a declared attribute key."""
    if isinstance(node, ast.Constant) and node.value is None:
        return "literal None"
    if isinstance(node, ast.IfExp):
        if any(
            isinstance(branch, ast.Constant) and branch.value is None
            for branch in (node.body, node.orelse)
        ):
            return "conditional None"
        return "uncoerced"
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        last = node.values[-1]
        if isinstance(last, ast.Constant) and last.value == "":
            return "coerced to ''"
        return "uncoerced"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str":
        return "str(...) — stringifies a None to 'None'"
    return "uncoerced"


def example_builder_sites(declared: set[str]) -> tuple[list[BuilderSite], int]:
    """Dict-literal sites in examples that feed a declared attribute key.

    Returns ``(sites, files_scanned)``. A key spelled as a module-level
    constant (``ATTR_NAME = "obligor_legal_name"``) is resolved through that
    constant, because the No-Hardcoding posture means example builders name
    their keys that way and a literal-only scan would see almost none of them.

    ``uncoerced`` is an honest *don't-know*: the value is an expression whose
    runtime type this scan cannot decide. It is reported as its own bucket
    rather than folded into either answer.
    """
    sites: list[BuilderSite] = []
    files = 0
    for path in sorted(REPO_ROOT.glob(EXAMPLE_BUILDER_GLOB)):
        files += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, ValueError) as exc:
            print(f"  ! could not parse {path} as python: {exc}", file=sys.stderr)
            continue
        constants: dict[str, str] = {}
        for statement in tree.body:
            if (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            ):
                constants[statement.targets[0].id] = statement.value.value
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key_node, value_node in zip(node.keys, node.values):
                if key_node is None:
                    continue
                name: str | None = None
                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                    name = key_node.value
                elif isinstance(key_node, ast.Name):
                    name = constants.get(key_node.id)
                if name is None or name not in declared:
                    continue
                sites.append(
                    BuilderSite(
                        source=rel,
                        line=value_node.lineno,
                        key=name,
                        shape=_value_shape(value_node),
                    )
                )
    return sites, files


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


# --------------------------------------------------------------------------
# The report's own positive control
# --------------------------------------------------------------------------

#: A synthetic ``INSERT`` exercising every shape the real fixtures use: a
#: multi-line column list, an interleaved comment, a JSON literal full of
#: commas and braces, an escaped quote, a quoted ``'null'`` that must NOT
#: match, and a trailing ``on conflict`` clause that must not be read as a row.
_CONTROL_SQL = """
insert into s.t
    (a, maturity_date, blob, note, b)
values
    -- a comment between tuples
    ('x', null, '{"k": [1, 2], "p": "(3, 4)"}', 'it''s fine', 1),
    ('y', '2026-01-01', '{}', 'null', 2)
on conflict (a) do update set b = 3;
"""


def positive_control() -> list[tuple[str, bool, str]]:
    """Drive the matchers over synthetic inputs whose answer is known.

    Returns ``(what_was_driven, fired_as_expected, observed)`` per control. A
    report that cannot show its own matcher firing cannot distinguish "nothing
    is there" from "nothing was looked at", which is the exact failure this
    tool was sent back to fix. Negative controls are here for the mirror
    failure: a matcher that fires on everything is equally useless.
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
            "NEGATIVE control: undeclared key carrying a null — must NOT fire",
            not _scan_json_structure(
                declared={"jurisdiction"},
                node={"something_else": None},
                locator_root="synthetic",
                source="<negative control>",
            )[0],
            "no hit",
        )
    )

    rows = list(sql_insert_rows(_CONTROL_SQL))
    arity_ok = all(len(columns) == len(tokens) for columns, _, tokens in rows)
    sql_hits = [
        (line, columns[index])
        for columns, line, tokens in rows
        for index, token in enumerate(tokens)
        if index < len(columns)
        and sql_token_null_reason(token) is not None
        and columns[index] in {"maturity_date"}
    ]
    controls.append(
        (
            "synthetic SQL INSERT: multi-line column list, comment between"
            " tuples, JSON literal, escaped quote, trailing `on conflict`",
            len(rows) == 2 and arity_ok and len(sql_hits) == 1,
            f"{len(rows)} row tuple(s) (expected 2), column/value arity"
            f" {'matched' if arity_ok else 'MISMATCHED'}, {len(sql_hits)} null"
            f" under 'maturity_date' (expected 1)",
        )
    )

    quoted_null = sql_token_null_reason("'null'")
    controls.append(
        (
            "NEGATIVE control: the quoted SQL string 'null' is a real value",
            quoted_null is None,
            f"sql_token_null_reason(\"'null'\") = {quoted_null!r}",
        )
    )

    sql_reasons = [
        sql_token_null_reason("null"),
        sql_token_null_reason(" NULL "),
        sql_token_null_reason("'NaN'::numeric"),
        sql_token_null_reason("'-Infinity'"),
        sql_token_null_reason("'2026-01-01'"),
        sql_token_null_reason("0"),
    ]
    controls.append(
        (
            "sql_token_null_reason over null / NULL / 'NaN'::numeric /"
            " '-Infinity' / a date / 0",
            sql_reasons == ["null", "null", "non-finite", "non-finite", None, None],
            str(sql_reasons),
        )
    )

    declared_control, unreadable_control = _python_declarations_from_text(
        'R(attribute_keys=("a", "b"))\nS(attribute_keys=tuple(x))\nT = {"attribute_keys": ["c"]}\n'
    )
    controls.append(
        (
            "inline Python declarations: keyword tuple, dict entry, and a"
            " COMPUTED one that must be reported unreadable",
            sorted(declared_control) == ["a", "b", "c"] and unreadable_control == [2],
            f"names={declared_control}, unreadable at line(s)={unreadable_control}",
        )
    )

    builder_shapes = _builder_shapes_from_text(
        'K = "jurisdiction"\n'
        "p = {K: None}\n"
        'q = {"jurisdiction": x if x else None}\n'
        'r = {"jurisdiction": x or ""}\n'
        's = {"jurisdiction": str(x)}\n'
        't = {"jurisdiction": x.y}\n'
        'u = {"undeclared": None}\n',
        declared={"jurisdiction"},
    )
    controls.append(
        (
            "example builder shapes: constant-named key, literal None,"
            " conditional None, `or \"\"`, str(...), bare attribute, and an"
            " undeclared key that must be skipped",
            builder_shapes
            == [
                "literal None",
                "conditional None",
                "coerced to ''",
                "str(...) — stringifies a None to 'None'",
                "uncoerced",
            ],
            str(builder_shapes),
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


def _python_declarations_from_text(text: str) -> tuple[list[str], list[int]]:
    """``_python_declarations`` over a string — the control's entry point."""
    tree = ast.parse(text)
    names: list[str] = []
    unreadable: list[int] = []
    for node in ast.walk(tree):
        values: list[ast.expr] = []
        if isinstance(node, ast.keyword) and node.arg == "attribute_keys":
            values.append(node.value)
        elif isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                if isinstance(key_node, ast.Constant) and key_node.value == "attribute_keys":
                    values.append(value_node)
        for value in values:
            literal = _literal_str_sequence(value)
            if literal is None:
                unreadable.append(value.lineno)
            else:
                names.extend(literal)
    return names, sorted(unreadable)


def _builder_shapes_from_text(text: str, *, declared: set[str]) -> list[str]:
    """``_value_shape`` over every declared-key dict entry in a string."""
    tree = ast.parse(text)
    constants: dict[str, str] = {}
    for statement in tree.body:
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            constants[statement.targets[0].id] = statement.value.value
    shapes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key_node, value_node in zip(node.keys, node.values):
            if key_node is None:
                continue
            name: str | None = None
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                name = key_node.value
            elif isinstance(key_node, ast.Name):
                name = constants.get(key_node.id)
            if name is None or name not in declared:
                continue
            shapes.append(_value_shape(value_node))
    return shapes


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _print_hit_groups(hits: list[Hit], indent: str = "    ") -> None:
    """Aggregate hits by ``(file, key, reason)`` and print counts plus lines.

    Individual hits are not printed one per line: the declared-name union
    reaches tens of thousands of rows in the census fixture, and a report a
    reader cannot finish is a report nobody checks. The *count* is always
    exact; only the line list is capped.
    """
    grouped: dict[tuple[str, str, str], list[str]] = collections.defaultdict(list)
    for hit in hits:
        grouped[(hit.source, hit.key, hit.reason)].append(hit.locator)
    for (source, key, reason) in sorted(grouped):
        locators = grouped[(source, key, reason)]
        shown = ", ".join(locators[:LINES_PER_GROUP])
        more = "" if len(locators) <= LINES_PER_GROUP else f", … {len(locators) - LINES_PER_GROUP} more"
        print(f"{indent}{source}: {key} = {reason} × {len(locators)} at {shown}{more}")


def _print_scoped_pairing(declarations: Declarations) -> int:
    """Pair each ``cp_NN_*.sql`` fixture with the ``cp-NN-*`` trees consuming it.

    Returns the product-scoped hit total. This is the precise number; the
    tree-wide union in section 2 is the ceiling.
    """
    per_tree = example_tree_declarations()
    total = 0
    # Derived from SQL_GLOB, not from a second glob of its own: two spellings
    # of "where the SQL rows live" drift apart, and a mutation that closed one
    # of them left this section still reporting hits the other had lost.
    for path in sorted(REPO_ROOT.glob(SQL_GLOB)):
        match = re.match(r"cp_(\d+)_.*_rows\.sql$", path.name)
        if match is None:
            continue
        rung = match.group(1)
        trees = sorted(tree for tree in per_tree if tree.startswith(f"cp-{rung}-"))
        scoped: set[str] = set()
        for tree in trees:
            scoped |= per_tree[tree]
        hits, stat = scan_sql(path=path, declared=scoped)
        total += len(hits)
        print(
            f"  {stat.source} ↔ {trees or '(no example tree)'}"
            f" — {len(scoped)} declared name(s); {stat.units} rows,"
            f" {stat.pairs} named values, {stat.null_any} null-like under ANY"
            f" column, {len(hits)} under a declared key"
        )
        _print_hit_groups(hits, indent="      ")
    return total


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
    print("--- 1. Declared attribute_keys names, by source ---")
    declarations = declared_attribute_keys()
    for glob, count in declarations.files_per_glob.items():
        print(f"  glob {glob}: {count} file(s) matched")
    for glob in declarations.empty_globs:
        print(f"  ! GLOB MATCHED NO FILES: {glob}")
        exit_code = 1
    if not declarations.by_key:
        print("  (none declared — the scan below cannot say anything; failing)")
        exit_code = 1
    print(f"  declaring sources: {len(declarations.by_source)}")
    for source, keys in declarations.by_source.items():
        print(f"    {source} ({len(keys)}): {', '.join(keys)}")
    print(
        f"  total distinct attribute-key names declared:"
        f" {len(declarations.by_key)}"
    )
    print(
        f"  declarations this scan CANNOT read (computed at runtime):"
        f" {len(declarations.unreadable)}"
    )
    for source, line in declarations.unreadable:
        print(f"    {source}:{line} — attribute_keys built from an expression")

    print()
    print("--- 2. Fixture rows carrying a null under a declared attribute key ---")
    hits, stats, empty_globs = scan_rows(declarations.names)
    print(f"  globs: {JSONL_GLOB}, {JSON_GLOB}, {SQL_GLOB}")
    for glob in empty_globs:
        print(
            f"  ! GLOB MATCHED NO FILES: {glob} — the scan below is empty by "
            "construction, not by measurement"
        )
        exit_code = 1
    print("  scanned (the denominators):")
    for stat in stats:
        unmatched = (
            "" if not stat.unmatched else f", {stat.unmatched} value(s) WITH NO COLUMN NAME"
        )
        print(
            f"    {stat.source}: {stat.units} {stat.unit}, {stat.pairs} key/value pairs"
            f" examined, {stat.null_any} null-like under ANY key, {stat.hits} under a"
            f" declared key{unmatched}"
        )
        if stat.error:
            print(f"      ! {stat.error}")
        if stat.unmatched or stat.error:
            exit_code = 1
    total_units = sum(stat.units for stat in stats)
    total_pairs = sum(stat.pairs for stat in stats)
    total_null_any = sum(stat.null_any for stat in stats)
    print(
        f"  totals: {len(stats)} files, {total_units} rows/mappings,"
        f" {total_pairs} key/value pairs examined"
    )
    print(f"  null-like values under ANY key (the don't-know discriminator): {total_null_any}")
    if hits:
        print(f"  {len(hits)} HIT(S) under a declared attribute key, grouped:")
        _print_hit_groups(hits)
    else:
        print("  0 hits under a declared attribute key.")
    print(f"  population size (tree-wide union — an UPPER BOUND): {len(hits)}")
    print(
        "  The union crosses products: a name declared by one example's rule can"
        " be null in another example's fixture, and those two never meet at"
        " runtime. Section 2b scopes it."
    )
    if not hits and total_null_any == 0:
        print(
            "  READ THIS AS DON'T-KNOW, NOT AS CLEAN: the scanned files carry no"
            " null-like value under ANY key, so this zero is a fact about the"
            " scan's reach, not about declared attribute keys."
        )

    print()
    print("--- 2b. Product-scoped: each cp_NN fixture vs. the cp-NN rules that read it ---")
    scoped_total = _print_scoped_pairing(declarations)
    print(f"  product-scoped population (the PRECISE number): {scoped_total}")

    print()
    print("--- 2c. Example payload builders feeding a declared attribute key ---")
    builder_sites, builder_files = example_builder_sites(declarations.names)
    shapes = collections.Counter(site.shape for site in builder_sites)
    print(f"  scanned: {EXAMPLE_BUILDER_GLOB} — {builder_files} file(s)")
    print(f"  declared-key dict sites found (the denominator): {len(builder_sites)}")
    for shape, count in sorted(shapes.items(), key=lambda item: (-item[1], item[0])):
        print(f"    {shape}: {count}")
    for shape in ("literal None", "conditional None"):
        named = [site for site in builder_sites if site.shape == shape]
        print(f"  sites passing a raw None — {shape} ({len(named)}):")
        for site in named:
            print(f"    {site.source}:{site.line} — {site.key}")
    uncoerced = collections.Counter(
        site.source for site in builder_sites if site.shape == "uncoerced"
    )
    print(
        f"  UNCOERCED (a don't-know: the value's runtime type is not statically"
        f" decidable) — {sum(uncoerced.values())} site(s) in {len(uncoerced)} file(s):"
    )
    for source, count in sorted(uncoerced.items()):
        print(f"    {source}: {count}")

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
        " D-IMPL-261). The str(...) bucket in section 2c is the same residual in"
        " a second spelling."
    )

    print()
    print("=" * 78)
    print("Summary")
    print("=" * 78)
    print(f"  declared attribute-key names (all sources) : {len(declarations.by_key)}")
    print(f"  declarations unreadable (computed)         : {len(declarations.unreadable)}")
    print(f"  files scanned for rows                     : {len(stats)}")
    print(f"  key/value pairs examined                   : {total_pairs}")
    print(f"  null-like under ANY key                    : {total_null_any}")
    print(f"  null-like under a DECLARED key (union)     : {len(hits)}")
    print(f"  null-like under a DECLARED key (scoped)    : {scoped_total}")
    print(f"  example builder sites on a declared key    : {len(builder_sites)}")
    print(f"  residual `or \"\"` sites upstream            : {site_count} ({file_count} files, {tree_count} trees)")
    print(f"  exit code                                  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
