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
yaml (**all** of it, not only ``ccf_config.yaml``: a rule-shaped mapping in
``examples/s1-01-hello-context-product/artifacts/resolution-spec.yaml``
declares 18 names that a ``ccf_config.yaml``-only glob missed while reporting no
hole), in spec fixtures elsewhere under ``tests/``, and inline in Python test
modules. All are read, and each source's own name set is printed separately so a
reader can see which declaration a hit came from rather than a merged blur.

**What the exit code cannot see.** This instrument is glob-driven. It detects a
glob that matched *nothing* — that fails the run — but it cannot detect a glob
that matched the *wrong subset*: narrowed so every glob still matches something,
it prints 13 names, a zero population, and exits **0**. The printed
declaring-source count and the per-source name sets are the only defense against
that, and reading them is a reader's job, not the exit code's. Section 1 says so
in its own output.

Because the merged name set is a **union across unrelated products**, a hit
against it is an upper bound: a name declared by one example's rule may be
null in a different example's fixture, and the two never meet at runtime. So
the report prints both numbers — the tree-wide union (upper bound) and a
**product-scoped** pairing that matches each ``cp_NN_*.sql`` fixture only
against the ``examples/cp-NN-*`` rules that actually consume it. The scoped
number is the precise one; the union number is the ceiling.

Two populations in the builder scan, too — and the scoped one leads
------------------------------------------------------------------

The same trap bit the builder measurement one round later, and in the other
direction: its count was a right number about the **wrong population**. Of the
declared-key dict entries anywhere under ``examples/``, roughly a quarter are
keyed by a name only a *different* tree or a test declares — generic keys like
``detail``, ``provenance``, ``note``, ``classification``, ``currency`` — and
most of the rest are dicts that are not payloads at all: params mappings,
expected-output fixtures, projection output rows. None of those is reachable by
a change to an attribute comprehension.

So section 2c leads with the **scoped** figure: a dict literal handed to a
``raw_payload=``/``payload=`` keyword argument, on a key the site's own example
tree declares. Both conditions are load-bearing, both are driven by positive
controls, and the unscoped figure is still printed — labeled as a loose upper
bound, for the denominator. **The honest number is smaller than the loose one,
and that is the point:** a measurement that shrinks under scoping and stays
true is worth more than a large one that does not.

The builder scan also carries the same UNREADABLE bucket the declarations
reader carries. It silently skipped dict keys it could not resolve to a
string — attribute accesses, subscripts, ``**`` splats, bare names, a call —
plus ``payload["key"] = ...`` subscript assignments, a readable key in a shape a
dict-literal walk never visits. An asymmetry between two halves of one
instrument is how a reader comes to trust the wrong half, so both halves now
report their holes.

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

The third member of that held question: blank strings
-----------------------------------------------------

The question actually being held is whether absence *rendered as data* should be
refused, and it has three members: a raw ``None``, a non-finite number, and an
**empty or whitespace-only string**. The first two were measured; the third had
no measurement behind it at all, which meant the owner was being asked to rule
on a population one third of which nobody had counted.

``blank_reason`` and ``sql_token_blank_reason`` close that, and they are
**reporting only**:

- They are separate functions from ``null_reason``/``sql_token_null_reason``, not
  a widening of them. One function returning both would make every null count in
  this report silently wider than the number it is labeled with.
- Blanks are counted and printed in their **own** section (2a) and their own
  summary rows. They are in no null total anywhere.
- A negative control pins ``null_reason("") is None``, so the SDK's ``is not
  None`` narrowness cannot be widened here by accident and then read back as
  measured.
- **No behavior changes.** An empty string is stored today exactly as it was
  before this tool existed. Section 2a makes the population visible so a ruling
  can be made against a number; making the ruling is not this tool's job.

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
#: Every yaml under ``examples/`` — **not** only ``ccf_config.yaml``. Measured
#: 2026-09-25: the narrower glob silently missed
#: ``examples/s1-01-hello-context-product/artifacts/resolution-spec.yaml:52``,
#: which declares five attribute keys in a rule-shaped mapping, and reported no
#: hole while doing it. A declaration source the instrument cannot see is the
#: same defect class as a fixture format it cannot reach, one level up. The
#: rule-shape filter in ``_iter_rule_like_mappings`` is what keeps the other 180+
#: yaml files (prose, gates, specs) out of the name set.
#:
#: One spelling, used by BOTH the tree-wide declaration union (section 1) and
#: the per-tree scoping (sections 2b and 2c): two spellings of "where examples
#: declare rules" is exactly the drift that left section 2b reporting hits
#: section 2 had lost.
EXAMPLE_YAML_GLOBS: tuple[str, ...] = ("examples/**/*.yaml", "examples/**/*.yml")

YAML_SPEC_GLOB_GROUPS: tuple[tuple[str, ...], ...] = (
    ("tests/**/*.yaml", "tests/**/*.yml"),
    EXAMPLE_YAML_GLOBS,
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

#: The keyword arguments whose dict-literal value is a **payload** — the only
#: dictionary a ``SpecDrivenEntityResolution`` attribute comprehension ever
#: reads. A dict literal anywhere else in an example (a params mapping, an
#: expected-output fixture, a projection's own output row) is not reachable by
#: the B4 change however its keys are spelled, so scoping on this is what turns
#: a right number about the wrong population into a right number about the
#: right one.
PAYLOAD_KWARGS: frozenset[str] = frozenset({"raw_payload", "payload"})

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
    #: The THIRD member of the held question (see ``blank_reason``): values that
    #: are present as data but carry no content. Counted and carried separately
    #: from ``null_any``/``hits`` on purpose — folding them in would silently
    #: widen the very population the project owner is being asked to rule on.
    blank_any: int = 0
    blanks: tuple["Hit", ...] = ()


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
    """One dict-literal site in an example that feeds a declared attribute key.

    ``tree``, ``payload_kwarg`` and ``own_tree_declares`` exist so the report can
    name **two** populations rather than one: every declared-key dict entry
    anywhere in ``examples/`` (the loose upper bound), and the entries the B4
    change can actually reach — a dict handed to a payload keyword argument, on
    a key the site's own example tree declares.
    """

    source: str
    line: int
    key: str
    shape: str
    #: ``examples/<tree>/...`` — the top-level example directory owning the file.
    tree: str
    #: The payload keyword argument this dict literal is the value of, or ``""``
    #: when the dict is not handed to one.
    payload_kwarg: str
    #: Whether ``tree``'s own resolution rules declare ``key``.
    own_tree_declares: bool

    @property
    def reachable(self) -> bool:
        """Both scoping conditions hold: a payload dict, on the tree's own key."""
        return bool(self.payload_kwarg) and self.own_tree_declares


class UnreadableKeys(NamedTuple):
    """Dict keys the builder scan could not resolve to a string, by shape.

    The declarations reader reports its three computed declarations as
    UNREADABLE, which is what makes its count honest. Before this round the
    builder scan had no equivalent and simply skipped what it could not read —
    an asymmetry between two halves of one instrument is how a reader comes to
    trust the wrong half.
    """

    by_shape: dict[str, int]
    #: ``payload["declared_key"] = ...`` — a *readable* declared key in a shape a
    #: dict-literal walk never visits. Not unreadable; unreached. The fourth
    #: element is the assignment kind (``"="`` / ``"augmented"`` / ``"annotated"``)
    #: so this count reconciles with a plain-assignment-only count of the same
    #: population rather than merely differing from it.
    subscript_assigned: list[tuple[str, int, str, str]]

    @property
    def total(self) -> int:
        return sum(self.by_shape.values())


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


def blank_reason(value: Any) -> str | None:
    """``"empty string"``, ``"whitespace-only string"``, or ``None``.

    **Reporting only. This changes no behavior anywhere.** The empty string is
    the third member of the question held for the project owner — whether
    absence rendered *as data* should be refused — and before this round it was
    the one member with no measurement behind it. ``null_reason`` deliberately
    does NOT report it (a negative control pins ``null_reason("") is None``), and
    the SDK's ``is not None`` test stays exactly as narrow as it is: an empty
    string is stored today and this tool does not change that. It only makes the
    population countable, so the ruling can be made against a number.

    Kept as a separate function from ``null_reason`` for that reason: one
    function returning both would make every existing count silently wider.
    """
    if not isinstance(value, str):
        return None
    if value == "":
        return "empty string"
    if value.strip() == "":
        return "whitespace-only string"
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

    Used for both product-scoped measurements: a ``cp_NN_*.sql`` fixture matched
    against the ``cp-NN-*`` trees that consume it (section 2b), and a builder
    site matched against its own tree's rules (section 2c). Reads
    ``EXAMPLE_YAML_GLOBS`` — the same constant section 1 reads, so a tree's
    declaration set cannot mean one thing in one section and another in another.
    """
    per_tree: dict[str, set[str]] = {}
    seen: set[pathlib.Path] = set()
    for glob in EXAMPLE_YAML_GLOBS:
        for path in sorted(REPO_ROOT.glob(glob)):
            if path in seen:
                continue
            seen.add(path)
            parts = path.relative_to(REPO_ROOT).parts
            if len(parts) < 2:
                continue
            tree = parts[1]
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


class StructureScan(NamedTuple):
    """One structural scan's hits and its denominators.

    A NamedTuple rather than a bare tuple because this round had to add a
    *second, separately counted* population (blanks) to it, and a positional
    3-tuple makes that change silently reorder at every call site.
    """

    hits: list[Hit]
    pairs: int
    null_any: int
    blank_any: int
    blanks: list[Hit]


def _scan_json_structure(
    *,
    declared: set[str],
    node: Any,
    locator_root: str,
    source: str,
) -> StructureScan:
    """Walk a parsed JSON structure, counting nulls and blanks separately."""
    hits: list[Hit] = []
    blanks: list[Hit] = []
    pairs = 0
    null_any = 0
    blank_any = 0
    for json_path, key, value in _iter_json_pairs(node, locator_root):
        pairs += 1
        reason = null_reason(value)
        if reason is not None:
            null_any += 1
            if key in declared:
                hits.append(
                    Hit(source=source, locator=f"{json_path}.{key}", key=key, reason=reason)
                )
            continue
        blank = blank_reason(value)
        if blank is not None:
            blank_any += 1
            if key in declared:
                blanks.append(
                    Hit(source=source, locator=f"{json_path}.{key}", key=key, reason=blank)
                )
    return StructureScan(
        hits=hits, pairs=pairs, null_any=null_any, blank_any=blank_any, blanks=blanks
    )


def scan_jsonl(*, path: pathlib.Path, declared: set[str]) -> tuple[list[Hit], ScanStat]:
    """Scan one ``.jsonl`` fixture — one row per non-blank line."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    hits: list[Hit] = []
    blanks: list[Hit] = []
    rows = pairs = null_any = blank_any = 0
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        rows += 1
        row = _scan_json_structure(
            declared=declared, node=json.loads(line), locator_root=f"line {line_no}", source=rel
        )
        hits.extend(row.hits)
        blanks.extend(row.blanks)
        pairs += row.pairs
        null_any += row.null_any
        blank_any += row.blank_any
    return hits, ScanStat(
        source=rel,
        unit="jsonl rows",
        units=rows,
        pairs=pairs,
        null_any=null_any,
        hits=len(hits),
        blank_any=blank_any,
        blanks=tuple(blanks),
    )


def scan_json(*, path: pathlib.Path, declared: set[str]) -> tuple[list[Hit], ScanStat]:
    """Scan one ``.json`` fixture document."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    document = json.loads(path.read_text(encoding="utf-8"))
    scan = _scan_json_structure(declared=declared, node=document, locator_root="$", source=rel)
    return scan.hits, ScanStat(
        source=rel,
        unit="json mappings",
        units=_count_mappings(document),
        pairs=scan.pairs,
        null_any=scan.null_any,
        hits=len(scan.hits),
        blank_any=scan.blank_any,
        blanks=tuple(scan.blanks),
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


def sql_token_blank_reason(token: str) -> str | None:
    """``"empty string"``, ``"whitespace-only string"``, or ``None``, for SQL.

    **Reporting only** — the SQL counterpart of ``blank_reason``. Only a *quoted*
    token can be blank: a bare ``null`` is already the null population, and an
    unquoted empty token is a parse artifact, not a value.

    A doubled single quote inside a quoted literal is an escaped quote, so the
    four-character token for the one-character string ``'`` must NOT read as
    blank. It does not, and **without any unescaping step**: whatever the escape
    spelling, the inner text still contains a quote character, and a string
    containing a quote is neither empty nor whitespace.

    That is stated rather than defended in code on purpose. A first version of
    this function unescaped the doubled quote before testing, and a negative
    control over that token passed either way — proven by exhaustion over every
    string of length <= 6 from ``{', space, x}``: there is **no** input whose
    blankness verdict the unescaping changes. The line was dead, the control
    could not tell, and a defensive line no control can redden is exactly the
    shape this wave is measuring. What the control does still catch is the
    plausible wrong implementation, ``strip("'")``, which reads that token as an
    empty string.
    """
    stripped = _CAST_RE.sub("", token.strip()).strip()
    if len(stripped) < 2 or stripped[0] != "'" or stripped[-1] != "'":
        return None
    core = stripped[1:-1]
    if core == "":
        return "empty string"
    if core.strip() == "":
        return "whitespace-only string"
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
    blanks: list[Hit] = []
    rows = pairs = null_any = blank_any = unmatched = 0
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
            if reason is not None:
                null_any += 1
                if column in declared:
                    hits.append(
                        Hit(source=rel, locator=f"line {line_number}", key=column, reason=reason)
                    )
                continue
            blank = sql_token_blank_reason(token)
            if blank is not None:
                blank_any += 1
                if column in declared:
                    blanks.append(
                        Hit(source=rel, locator=f"line {line_number}", key=column, reason=blank)
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
        blank_any=blank_any,
        blanks=tuple(blanks),
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


def _payload_dict_kwargs(tree: ast.AST) -> dict[int, str]:
    """``id(dict_node) -> keyword name`` for every payload dict literal in a file.

    Only the dict that *is* the keyword argument's value counts. A nested dict
    inside a payload is not itself the mapping the attribute comprehension reads,
    and counting it would re-inflate the population this scoping exists to
    narrow.
    """
    payloads: dict[int, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if (
                keyword.arg in PAYLOAD_KWARGS
                and isinstance(keyword.value, ast.Dict)
            ):
                payloads[id(keyword.value)] = keyword.arg
    return payloads


def _unreadable_key_shape(key_node: ast.expr | None) -> str:
    """Name the shape of a dict key this scan cannot resolve to a string."""
    if key_node is None:
        return "dictionary splat (**other)"
    if isinstance(key_node, ast.Attribute):
        return "attribute access"
    if isinstance(key_node, ast.Subscript):
        return "subscript"
    if isinstance(key_node, ast.Name):
        return "bare name (not a module-level string constant)"
    if isinstance(key_node, ast.Call):
        return "call"
    if isinstance(key_node, ast.Constant):
        return f"non-string constant ({type(key_node.value).__name__})"
    return type(key_node).__name__


def _subscript_assigned_keys(
    tree: ast.AST, *, declared: set[str], rel: str
) -> list[tuple[str, int, str]]:
    """``payload["declared_key"] = ...`` sites — readable keys, unreached shape.

    A dict-literal walk never visits these, so without this list the builder
    section would report a denominator that excludes a shape it silently cannot
    see. Reported beside the unreadable bucket rather than folded into the site
    count, because these are not dict-literal sites and the shape of their value
    is a different question.
    """
    found: list[tuple[str, int, str, str]] = []
    for node in ast.walk(tree):
        targets: list[tuple[ast.expr, str]] = []
        if isinstance(node, ast.Assign):
            targets.extend((target, "=") for target in node.targets)
        elif isinstance(node, ast.AugAssign):
            targets.append((node.target, "augmented"))
        elif isinstance(node, ast.AnnAssign):
            targets.append((node.target, "annotated"))
        for target, kind in targets:
            if not isinstance(target, ast.Subscript):
                continue
            index = target.slice
            if (
                isinstance(index, ast.Constant)
                and isinstance(index.value, str)
                and index.value in declared
            ):
                found.append((rel, target.lineno, index.value, kind))
    return found


class ModuleScan(NamedTuple):
    """One example module's builder sites, plus what the walk could not read."""

    sites: list[BuilderSite]
    unreadable: collections.Counter[str]
    subscript_assigned: list[tuple[str, int, str]]


def _builder_sites_in_module(
    tree: ast.AST,
    *,
    declared: set[str],
    rel: str,
    example_tree: str,
    own_keys: set[str],
) -> ModuleScan:
    """The one walk. Both the disk scan and the positive control call THIS.

    Section 2b was already bitten once by two spellings of the same question
    drifting apart, so the control drives the same function the report does
    rather than a copy of it: a control over a copy proves the copy.
    """
    constants: dict[str, str] = {}
    for statement in getattr(tree, "body", []):
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            constants[statement.targets[0].id] = statement.value.value

    payloads = _payload_dict_kwargs(tree)
    sites: list[BuilderSite] = []
    unreadable: collections.Counter[str] = collections.Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        kwarg = payloads.get(id(node), "")
        for key_node, value_node in zip(node.keys, node.values):
            name: str | None = None
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                name = key_node.value
            elif isinstance(key_node, ast.Name):
                name = constants.get(key_node.id)
            if name is None:
                unreadable[_unreadable_key_shape(key_node)] += 1
                continue
            if name not in declared:
                continue
            sites.append(
                BuilderSite(
                    source=rel,
                    line=value_node.lineno,
                    key=name,
                    shape=_value_shape(value_node),
                    tree=example_tree,
                    payload_kwarg=kwarg,
                    own_tree_declares=name in own_keys,
                )
            )
    return ModuleScan(
        sites=sites,
        unreadable=unreadable,
        subscript_assigned=_subscript_assigned_keys(tree, declared=declared, rel=rel),
    )


def example_builder_sites(
    declared: set[str],
) -> tuple[list[BuilderSite], int, UnreadableKeys]:
    """Dict-literal sites in examples that feed a declared attribute key.

    Returns ``(sites, files_scanned, unreadable)``. A key spelled as a
    module-level constant (``ATTR_NAME = "obligor_legal_name"``) is resolved
    through that constant, because the No-Hardcoding posture means example
    builders name their keys that way and a literal-only scan would see almost
    none of them.

    ``uncoerced`` is an honest *don't-know*: the value is an expression whose
    runtime type this scan cannot decide. It is reported as its own bucket
    rather than folded into either answer.

    Each site also carries its scoping facts (``tree``, ``payload_kwarg``,
    ``own_tree_declares``) so the report can lead with the population the B4
    change can actually reach instead of with a tree-wide ceiling.
    """
    per_tree = example_tree_declarations()
    sites: list[BuilderSite] = []
    unreadable_shapes: collections.Counter[str] = collections.Counter()
    subscript_assigned: list[tuple[str, int, str, str]] = []
    files = 0
    for path in sorted(REPO_ROOT.glob(EXAMPLE_BUILDER_GLOB)):
        files += 1
        try:
            module = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, ValueError) as exc:
            print(f"  ! could not parse {path} as python: {exc}", file=sys.stderr)
            continue
        relative = path.relative_to(REPO_ROOT)
        example_tree = relative.parts[1] if len(relative.parts) > 1 else ""
        scan = _builder_sites_in_module(
            module,
            declared=declared,
            rel=relative.as_posix(),
            example_tree=example_tree,
            own_keys=per_tree.get(example_tree, set()),
        )
        sites.extend(scan.sites)
        unreadable_shapes.update(scan.unreadable)
        subscript_assigned.extend(scan.subscript_assigned)
    return (
        sites,
        files,
        UnreadableKeys(
            by_shape=dict(unreadable_shapes),
            subscript_assigned=sorted(subscript_assigned),
        ),
    )


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
    scan = _scan_json_structure(
        declared={"jurisdiction", "currency"},
        node=nested,
        locator_root="synthetic",
        source="<positive control>",
    )
    controls.append(
        (
            "nested JSON row, null under a declared key at depth 2",
            [h.key for h in scan.hits] == ["jurisdiction", "currency"],
            f"{len(scan.hits)} hit(s) {[h.key + '=' + h.reason for h in scan.hits]}"
            f" over {scan.pairs} pairs, {scan.null_any} null-like under any key",
        )
    )

    clean = {"after": {"jurisdiction": "IE", "currency": "USD"}}
    clean_scan = _scan_json_structure(
        declared={"jurisdiction", "currency"},
        node=clean,
        locator_root="synthetic",
        source="<negative control>",
    )
    controls.append(
        (
            "NEGATIVE control: same keys, real values — must NOT fire",
            not clean_scan.hits and clean_scan.null_any == 0 and clean_scan.blank_any == 0,
            f"{len(clean_scan.hits)} hit(s), {clean_scan.null_any} null-like,"
            f" {clean_scan.blank_any} blank",
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
            ).hits,
            "no hit",
        )
    )

    blank_scan = _scan_json_structure(
        declared={"jurisdiction", "currency"},
        node={"after": {"jurisdiction": "", "currency": "   ", "note": ""}},
        locator_root="synthetic",
        source="<positive control>",
    )
    controls.append(
        (
            "blank strings are a SEPARATE population: 2 declared blanks counted"
            " as blanks, 0 as nulls, and the undeclared one outside the hit list",
            (
                not blank_scan.hits
                and blank_scan.null_any == 0
                and blank_scan.blank_any == 3
                and [(h.key, h.reason) for h in blank_scan.blanks]
                == [("jurisdiction", "empty string"), ("currency", "whitespace-only string")]
            ),
            f"{len(blank_scan.hits)} null hit(s), {blank_scan.null_any} null-like,"
            f" {blank_scan.blank_any} blank under ANY key,"
            f" declared blanks {[(h.key, h.reason) for h in blank_scan.blanks]}",
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

    sql_blanks = [
        sql_token_blank_reason("''"),
        sql_token_blank_reason("'   '"),
        sql_token_blank_reason("''::text"),
        sql_token_blank_reason("''''"),
        sql_token_blank_reason("'x'"),
        sql_token_blank_reason("null"),
        sql_token_blank_reason("0"),
    ]
    controls.append(
        (
            "sql_token_blank_reason over '' / '   ' / ''::text / an ESCAPED quote"
            " / 'x' / null / 0 — the escaped quote is a real one-character value",
            sql_blanks
            == [
                "empty string",
                "whitespace-only string",
                "empty string",
                None,
                None,
                None,
                None,
            ],
            str(sql_blanks),
        )
    )

    blank_reasons = [
        blank_reason(""),
        blank_reason("   "),
        blank_reason("\t\n"),
        blank_reason("x"),
        blank_reason(None),
        blank_reason(0),
        blank_reason([]),
    ]
    controls.append(
        (
            "blank_reason over '' / spaces / tab+newline / 'x' / None / 0 / []"
            " — and null_reason('') stays None, which is the HELD narrowness",
            blank_reasons
            == [
                "empty string",
                "whitespace-only string",
                "whitespace-only string",
                None,
                None,
                None,
                None,
            ]
            and null_reason("") is None,
            f"{blank_reasons}, null_reason('') = {null_reason('')!r}",
        )
    )

    scoping = _builder_scan_from_text(
        'ENTITY = {"jurisdiction": None}\n'
        'resolve(raw_payload={"jurisdiction": None})\n'
        'resolve(payload={"jurisdiction": None})\n'
        'resolve(params={"jurisdiction": None})\n'
        'resolve(raw_payload={"jurisdiction": {"jurisdiction": None}})\n',
        declared={"jurisdiction"},
    )
    controls.append(
        (
            "payload scoping: of 6 declared-key sites only the 3 whose OWN dict"
            " is a raw_payload=/payload= value are reachable — a bare dict, a"
            " params= dict, and a dict NESTED inside a payload are not",
            (
                len(scoping.sites) == 6
                and [site.payload_kwarg for site in scoping.sites]
                == ["", "raw_payload", "payload", "", "raw_payload", ""]
                and sum(site.reachable for site in scoping.sites) == 3
            ),
            f"{len(scoping.sites)} site(s), kwargs"
            f" {[site.payload_kwarg for site in scoping.sites]},"
            f" {sum(site.reachable for site in scoping.sites)} reachable",
        )
    )

    foreign = _builder_scan_from_text(
        'resolve(raw_payload={"jurisdiction": None, "detail": None})\n',
        declared={"jurisdiction", "detail"},
        own_keys={"jurisdiction"},
    )
    controls.append(
        (
            "tree scoping: a payload key declared only by ANOTHER tree is a site"
            " but NOT reachable — this is the 398-site correction, mechanized",
            (
                [(s.key, s.own_tree_declares, s.reachable) for s in foreign.sites]
                == [("jurisdiction", True, True), ("detail", False, False)]
            ),
            str([(s.key, s.own_tree_declares, s.reachable) for s in foreign.sites]),
        )
    )

    unreadable_control = _builder_scan_from_text(
        'other = {"jurisdiction": 1}\n'
        'a = {obj.attr: None}\n'
        'b = {mapping["k"]: None}\n'
        'c = {undefined_name: None}\n'
        'd = {f(): None}\n'
        'e = {1: None}\n'
        'g = {**other, "jurisdiction": None}\n'
        'payload = {}\n'
        'payload["jurisdiction"] = None\n'
        'payload["undeclared"] = None\n',
        declared={"jurisdiction"},
    )
    controls.append(
        (
            "UNREADABLE key bucket: attribute, subscript, bare name, call, and a"
            " non-string constant are each named; a ** splat is named; and a"
            " subscript ASSIGNMENT to a declared key is reported as unreached",
            (
                unreadable_control.unreadable
                == collections.Counter(
                    {
                        "attribute access": 1,
                        "subscript": 1,
                        "bare name (not a module-level string constant)": 1,
                        "call": 1,
                        "non-string constant (int)": 1,
                        "dictionary splat (**other)": 1,
                    }
                )
                and [
                    (key, kind)
                    for _, _, key, kind in unreadable_control.subscript_assigned
                ]
                == [("jurisdiction", "=")]
            ),
            f"{dict(unreadable_control.unreadable)}, subscript-assigned"
            f" {unreadable_control.subscript_assigned}",
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


def _builder_scan_from_text(
    text: str, *, declared: set[str], own_keys: set[str] | None = None
) -> ModuleScan:
    """``_builder_sites_in_module`` over a string — the control's entry point.

    Drives the SAME walk the disk scan drives (see that function's docstring on
    why a copy would prove only the copy).
    """
    return _builder_sites_in_module(
        ast.parse(text),
        declared=declared,
        rel="<control>",
        example_tree="control-tree",
        own_keys=declared if own_keys is None else own_keys,
    )


def _builder_shapes_from_text(text: str, *, declared: set[str]) -> list[str]:
    """``_value_shape`` over every declared-key dict entry in a string."""
    return [site.shape for site in _builder_scan_from_text(text, declared=declared).sites]


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
        "  READ THE DECLARING-SOURCE COUNT ABOVE, NOT THE EXIT CODE: this"
        " instrument is glob-driven, so it can detect a glob that matched"
        " NOTHING (it fails the run) but NOT a glob that matched the WRONG"
        " SUBSET. Narrowed so every glob still matches something, this tool"
        " prints 13 names, a zero population, and exits 0. The printed count of"
        " declaring sources and their per-file name sets are the only defense"
        " against that, and they are a reader's job, not the exit code's."
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
    total_blank_any = sum(stat.blank_any for stat in stats)
    blank_hits = [hit for stat in stats for hit in stat.blanks]
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
    print("--- 2a. Empty and whitespace-only strings — a SEPARATE population ---")
    print(
        "  REPORTING ONLY. No behavior anywhere changes for these, and the SDK's"
        " `is not None` test is NOT widened to reach them: an empty string is"
        " stored today, exactly as it was before this tool existed."
    )
    print(
        "  Why they are counted at all: the question held for the project owner"
        " is whether absence RENDERED AS DATA should be refused, and the empty"
        " string is its third member (beside a raw null and a non-finite"
        " number). It was the one member with no measurement behind it. A ruling"
        " cannot be made against a population nobody has counted."
    )
    for stat in stats:
        if stat.blank_any or stat.blanks:
            print(
                f"    {stat.source}: {stat.blank_any} blank string(s) under ANY key,"
                f" {len(stat.blanks)} under a DECLARED attribute key"
            )
    print(f"  blank strings under ANY key (all files)          : {total_blank_any}")
    print(f"  blank strings under a DECLARED attribute key     : {len(blank_hits)}")
    if blank_hits:
        _print_hit_groups(blank_hits)
    print(
        "  These are NOT in any null count printed above or below: `null_reason`"
        " returns None for them by design, a negative control pins that, and"
        " folding the two populations together would silently widen the number"
        " the ruling is about."
    )

    print()
    print("--- 2b. Product-scoped: each cp_NN fixture vs. the cp-NN rules that read it ---")
    scoped_total = _print_scoped_pairing(declarations)
    print(f"  product-scoped population (the PRECISE number): {scoped_total}")

    print()
    print("--- 2c. Example payload builders feeding a declared attribute key ---")
    builder_sites, builder_files, unreadable_keys = example_builder_sites(declarations.names)
    reachable = [site for site in builder_sites if site.reachable]
    print(f"  scanned: {EXAMPLE_BUILDER_GLOB} — {builder_files} file(s)")
    print()
    print("  (i) SCOPED — the population the B4 change can actually reach.")
    print(
        "      Definition: a dict literal handed to a"
        f" {'/'.join(sorted(PAYLOAD_KWARGS))} keyword argument, on a key the"
        " site's OWN example tree declares. Both conditions are load-bearing:"
        " a dict that is not a payload never reaches an attribute comprehension,"
        " and a key only another tree declares never meets this tree's rules at"
        " runtime."
    )
    print(f"      payload-dict sites on the tree's own declared key: {len(reachable)}")
    scoped_shapes = collections.Counter(site.shape for site in reachable)
    for shape, count in sorted(scoped_shapes.items(), key=lambda item: (-item[1], item[0])):
        print(f"        {shape}: {count}")
    for shape in ("literal None", "conditional None"):
        named = [site for site in reachable if site.shape == shape]
        print(f"      SCOPED sites passing a raw None — {shape} ({len(named)}):")
        for site in named:
            print(f"        {site.source}:{site.line} — {site.key} [{site.payload_kwarg}=]")
    print()
    print("  (ii) UNSCOPED — every declared-key dict entry anywhere in examples/.")
    print(
        "       A LOOSE UPPER BOUND, printed for the denominator and not to be"
        " quoted as the population: it counts dicts that are not payloads at all"
        " (params mappings, expected-output fixtures, projection output rows) and"
        " keys generic enough that another tree or a test declares them"
        " (`detail`, `provenance`, `note`, `classification`, `currency`)."
    )
    shapes = collections.Counter(site.shape for site in builder_sites)
    print(f"       declared-key dict sites found: {len(builder_sites)}")
    for shape, count in sorted(shapes.items(), key=lambda item: (-item[1], item[0])):
        print(f"         {shape}: {count}")
    in_payload = sum(1 for site in builder_sites if site.payload_kwarg)
    own_key = sum(1 for site in builder_sites if site.own_tree_declares)
    print(
        f"       of these: {in_payload} are in a payload dict,"
        f" {own_key} are on a key the site's own tree declares,"
        f" {len(reachable)} are both"
    )
    print(
        f"       and {len(builder_sites) - own_key} are keyed by a name only a"
        " DIFFERENT tree or a test declares"
    )
    for shape in ("literal None", "conditional None"):
        named = [site for site in builder_sites if site.shape == shape]
        print(f"       UNSCOPED sites passing a raw None — {shape} ({len(named)}):")
        for site in named:
            marker = "REACHABLE" if site.reachable else "out of scope"
            why = (
                ""
                if site.payload_kwarg
                else " (not a payload dict)"
            )
            if site.payload_kwarg and not site.own_tree_declares:
                why = " (key declared only by another tree)"
            print(f"         {site.source}:{site.line} — {site.key} [{marker}{why}]")
    uncoerced = collections.Counter(
        site.source for site in builder_sites if site.shape == "uncoerced"
    )
    print(
        f"       UNCOERCED (a don't-know: the value's runtime type is not"
        f" statically decidable) — {sum(uncoerced.values())} site(s) in"
        f" {len(uncoerced)} file(s):"
    )
    for source, count in sorted(uncoerced.items()):
        print(f"         {source}: {count}")
    print()
    print("  (iii) What this walk CANNOT read — the builder scan's own hole.")
    print(
        "        The declarations reader reports its computed declarations as"
        " UNREADABLE, which is what makes its count honest. This half had no"
        " equivalent and silently skipped what it could not resolve; an"
        " asymmetry between two halves of one instrument is how a reader comes"
        " to trust the wrong half."
    )
    print(f"        dict keys not resolvable to a string: {unreadable_keys.total}")
    for shape, count in sorted(
        unreadable_keys.by_shape.items(), key=lambda item: (-item[1], item[0])
    ):
        print(f"          {shape}: {count}")
    print(
        "        Any of these could be spelling a declared attribute key at"
        " runtime, so every count in (i) and (ii) is a LOWER bound by this much."
    )
    print(
        "        The bare-name bucket is the RESIDUAL after constant resolution:"
        " a key spelled as a module-level string constant is resolved through it"
        " and counted as read, not as unreadable. A scan that did not resolve"
        " them would report a far larger bucket for the same tree."
    )
    by_kind = collections.Counter(kind for *_, kind in unreadable_keys.subscript_assigned)
    print(
        f"        declared keys assigned by SUBSCRIPT — a readable key in a shape"
        f" this dict-literal walk never visits: {len(unreadable_keys.subscript_assigned)}"
        f" ({', '.join(f'{count} {kind}' for kind, count in sorted(by_kind.items()))})"
    )
    for source, line, key, kind in unreadable_keys.subscript_assigned:
        print(f"          {source}:{line} — {key} [{kind}]")
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
    print(f"  blank strings under ANY key (separate)     : {total_blank_any}")
    print(f"  blank strings under a DECLARED key         : {len(blank_hits)}")
    print(f"  builder sites REACHABLE (payload + own key): {len(reachable)}")
    print(f"    of those, literal None                   : {sum(1 for s in reachable if s.shape == 'literal None')}")
    print(f"    of those, conditional None               : {sum(1 for s in reachable if s.shape == 'conditional None')}")
    print(f"    of those, uncoerced (don't-know)          : {sum(1 for s in reachable if s.shape == 'uncoerced')}")
    print(f"  builder sites UNSCOPED (an upper bound)    : {len(builder_sites)}")
    print(f"  builder dict keys UNREADABLE               : {unreadable_keys.total}")
    print(f"  residual `or \"\"` sites upstream            : {site_count} ({file_count} files, {tree_count} trees)")
    print(f"  exit code                                  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
