"""Does any subject or string parameter the shipped examples use fall outside the floor?

`D-IMPL-357` C5, the adoption question C1/C1a raise. Wave 1 put a mechanism
character grammar (`src/ccf/products/request.py::SUBJECT_FLOOR_V1`) in front of
every product request and judged it before any data acquisition
(`src/ccf/products/request.py::refuse_floor`). A grammar that refuses a value
a shipped example actually asks with would break that example at the door, so
the question has to be *measured* over the tree rather than reasoned about.
The recon expects zero. This module is what turns that expectation into a
number a reader can check.

STRICTLY READ-ONLY, AND STRUCTURALLY SO
---------------------------------------
It opens files for reading, matches text against one compiled pattern, and
prints. It writes no file, mutates nothing, spawns no subprocess, opens no
socket and reads no clock: the only filesystem call below is
`pathlib.Path.read_text`, and the whole import list is `argparse`, `ast`,
`os`, `pathlib`, `sys`, `dataclasses`, `typing`, `yaml`, and three names out
of `src/ccf/products/request.py` — no `subprocess`, no `socket`, no HTTP
client, no database driver and no `datetime`. Nothing it does can reach
`192.168.4.76` or any other estate host.

THE MODE IT RUNS IN, STATED RATHER THAN LEFT TO A READER TO GUESS
----------------------------------------------------------------
There are two subjects an example can ask with: the **literal** declared in
its own artifacts and code, and the **estate-resolved** value an example
derives at run time from a live store. This probe covers the first and says
so in its own output, naming the count of `CCF_CP_*` variables present so a
reader knows whether an estate-resolved pass was even possible. It does not
implement the second, and the omission is deliberate rather than accidental:
resolving an estate subject means running an example against `.76`, which
would cost this module its read-only promise above. The estate-resolved
subjects are covered instead by the wave's own estate-gated run, which
executes the example suite read-only against the curated stores. **What this
probe reports about estate-resolved subjects is therefore: don't know.**

WHAT IT CANNOT TELL, STATED BECAUSE A ZERO FROM AN INSTRUMENT THAT CANNOT
REFUSE IS WORTHLESS
------------------------------------------------------------------------
* **It classifies positions, and the classification is the author's.** Only
  some of the `subject`-named values in this tree are `ProductRequest`
  subjects: `examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml`
  names each operator step's `subject:` in prose, and
  `tests/examples/test_cp_04_seams.py::batching_violations` takes a `subject=`
  that is a message label. Those are not positions `refuse_floor` reaches, so
  the matcher's verdict on them is reported and is not a finding. Every such
  verdict is printed in full with the evidence for its classification, so a
  reader can overturn the author's call rather than take it on trust.
* **It reads declarations, not effective requests.** A default the resolution
  stage supplies, a policy-narrowed value and a relative default never appear
  as a declared literal, and `refuse_floor` does not judge them either — its
  own docstring names that boundary.
* **A dynamic expression is never a pass.** A subject read out of a fixture, a
  parameter or a live store at run time has no literal to match. Where the
  name resolves to a module-level string binding the probe folds it and judges
  the value; where it does not, the position is reported as an UNRESOLVED
  residual with the node type that defeated it, and is never counted among the
  values that passed.
* **An empty glob is a failure, not a clean run.** A source glob that matches
  no files means the probe has stopped looking at something, which reads
  exactly like a tree with nothing to find. That exits 2 by itself.

THREE EXIT CODES, BECAUSE THERE ARE THREE ANSWERS
-------------------------------------------------
``0`` **PASS** — the population is non-empty, the control fired, and no value
at a position `refuse_floor` judges lies outside the grammar. ``1``
**REFUSED** — at least one judged value is outside the grammar; the report
names it. ``2`` **COULD-NOT-TELL** — a source glob matched nothing, a file
failed to parse, or the positive control did not fire, so the instrument
cannot be trusted and its zero means nothing. Collapsing ``2`` into ``0`` is
the specific failure this module is built against.

THE POSITIVE CONTROL
--------------------
`positive_control` runs the same matcher over five values known to lie outside
the grammar — both quote characters, an angle bracket, a leading hyphen and a
513-character value — and one built from the allowlist that must pass. The run
exits non-zero if any of the five fails to refuse or the sixth fails to pass,
because a probe that reports zero refusals has said nothing until it has shown
it can produce one.

Usage::

    PYTHONPATH=src:runtime python tools/probe_subject_floor.py
    PYTHONPATH=src:runtime python tools/probe_subject_floor.py --root /path/to/tree
"""

from __future__ import annotations

import argparse
import ast
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Iterator, Sequence

import yaml

from ccf.products.request import (
    SUBJECT_FLOOR_V1,
    SUBJECT_FLOOR_VERSION,
    ProductRequest,
)

# --- what the probe looks at -----------------------------------------------

#: The source globs, each with the value class it yields. Every one of these
#: MUST match at least one file: a glob that matches nothing is a don't-know
#: reported as a pass, which is the failure mode this probe exists to avoid.
SOURCES: tuple[tuple[str, str], ...] = (
    ("example-artifact-yaml", "examples/**/*.yaml"),
    ("example-code-py", "examples/**/*.py"),
    ("example-test-py", "tests/examples/*.py"),
)

#: The field names of the request the floor judges, taken from the contract
#: itself rather than retyped here, so a field added to
#: `src/ccf/products/request.py::ProductRequest` widens this probe's notion of
#: "request-shaped" without an edit.
REQUEST_FIELDS: frozenset[str] = frozenset(ProductRequest.model_fields)

#: The mapping key whose string values at any depth ARE the positions
#: `refuse_floor` walks after the subject.
PARAMETERS_KEY: str = "parameters"

#: The call whose `subject=` and `parameters=` keywords are the judged
#: positions in Python. Taken from the class, not spelled again.
REQUEST_CALLEE: str = ProductRequest.__name__

#: Mapping keys whose child mapping is a question or a request by name, used
#: as one of the three request-shaped tests below. These are classification
#: vocabulary for this instrument, not fabric mechanism.
REQUEST_SHAPED_PARENT_KEYS: frozenset[str] = frozenset({"question", "request"})

#: Python names whose module-level string binding is a subject by convention in
#: the example tests (`SUBJECT`, `ANCHOR`, `UNANSWERABLE_SUBJECT`).
SUBJECT_NAME_SUFFIXES: tuple[str, ...] = ("SUBJECT", "ANCHOR")

#: Directories never walked.
SKIP_DIRS: frozenset[str] = frozenset({".git", "__pycache__", ".venv", "site"})

#: The environment-variable prefix whose presence would have made an
#: estate-resolved pass possible. Reported, never read for a value.
ESTATE_PREFIX: str = "CCF_CP_"

#: Call names whose result is a parsed YAML document. A module binding built
#: from one of these holds values this probe judges at their YAML source, so a
#: `subject=QUESTION[...][...]` off such a binding is reported as that rather
#: than as an unknown.
YAML_LOADERS: frozenset[str] = frozenset(
    {"safe_load", "safe_load_all", "compose", "compose_all", "full_load", "load"}
)


# --- the record a reader adjudicates --------------------------------------


@dataclass(frozen=True)
class Value:
    """One string found at one position, with the verdict and the reason for it."""

    kind: str
    path: str
    line: int
    key: str
    value: str
    judged: bool
    why: str

    @property
    def refuses(self) -> bool:
        """Does the mechanism floor refuse this text?"""
        return SUBJECT_FLOOR_V1.fullmatch(self.value) is None

    @property
    def verdict(self) -> str:
        """`pass` or `REFUSE`, printed per value beside its position."""
        return "REFUSE" if self.refuses else "pass"

    def line_out(self) -> str:
        """`path:line key value -> verdict`, the one-line report form."""
        shown = self.value if len(self.value) <= 72 else f"{self.value[:69]}..."
        judged = "judged" if self.judged else "not-judged"
        return (
            f"  {self.path}:{self.line} [{self.kind}/{judged}] {self.key}"
            f" = {shown!r} -> {self.verdict}"
        )


#: The residual class for a position whose value the source does not hold.
UNRESOLVED: str = "value-not-in-the-source"

#: The residual class for a position holding something that is not a string.
#: Fully known, and outside what `refuse_floor` judges — it walks declared
#: `string` positions only.
NOT_A_STRING: str = "not-a-string"


@dataclass(frozen=True)
class Unresolved:
    """A collected position that yielded no verdict, with the class of why.

    Two classes, kept apart because they mean opposite things. `UNRESOLVED` is
    a don't-know: `refuse_floor` judges the effective value at run time and the
    effective value here comes from a fixture, a function parameter or the
    estate. `NOT_A_STRING` is fully known and simply out of scope. Both are
    printed in full, because a residual nobody can see is the same as a
    residual nobody stated.
    """

    cls: str
    path: str
    line: int
    why: str
    detail: str

    def line_out(self) -> str:
        """`path:line detail — why`, the one-line report form."""
        return f"  {self.path}:{self.line} {self.detail} — {self.why}"


@dataclass(frozen=True)
class Error:
    """A file the probe could not read or parse at all. An instrument failure."""

    path: str
    line: int
    detail: str

    def line_out(self) -> str:
        """`path:line detail`, the one-line report form."""
        return f"  {self.path}:{self.line} {self.detail}"


# --- YAML ------------------------------------------------------------------


def _scalar_strings(node: yaml.Node) -> Iterator[tuple[int, str]]:
    """Every string scalar at any depth under `node`, with its 1-based line."""
    if isinstance(node, yaml.ScalarNode):
        if node.tag == "tag:yaml.org,2002:str":
            yield node.start_mark.line + 1, str(node.value)
        return
    if isinstance(node, yaml.SequenceNode):
        for child in node.value:
            yield from _scalar_strings(child)
        return
    if isinstance(node, yaml.MappingNode):
        for _key, child in node.value:
            yield from _scalar_strings(child)


def _request_shaped(
    *, sibling_keys: frozenset[str], parent_key: str | None, filename: str
) -> tuple[bool, str]:
    """Is the mapping holding this `subject` a question the floor would judge?

    Three independent tests, and the reason the answer came out the way it did
    is returned with it so the report can print it. (a) the mapping carries
    another field of the request contract; (b) the mapping is itself the value
    of a `question`/`request` key; (c) the document is a question document by
    filename. Any one suffices.
    """
    shared = sorted(sibling_keys & (REQUEST_FIELDS - {"subject"}))
    if shared:
        return True, f"sibling request fields {shared}"
    if parent_key in REQUEST_SHAPED_PARENT_KEYS:
        return True, f"parent key {parent_key!r}"
    if filename.startswith("question") or filename.endswith("question.yaml"):
        return True, f"question document {filename!r}"
    return False, (
        f"no request field among siblings {sorted(sibling_keys)},"
        f" parent key {parent_key!r}, file {filename!r}"
    )


def _walk_mapping(
    node: yaml.MappingNode,
    *,
    rel: str,
    filename: str,
    parent_key: str | None,
    values: list[Value],
) -> None:
    """Collect `subject`-suffixed strings and `parameters` strings under one mapping."""
    keys = frozenset(
        str(key.value) for key, _ in node.value if isinstance(key, yaml.ScalarNode)
    )
    for key_node, child in node.value:
        if not isinstance(key_node, yaml.ScalarNode):
            continue
        key = str(key_node.value)
        if key == PARAMETERS_KEY:
            for line, text in _scalar_strings(child):
                values.append(
                    Value(
                        kind="yaml-parameter",
                        path=rel,
                        line=line,
                        key=key,
                        value=text,
                        judged=True,
                        why="a string under `parameters`, which refuse_floor walks",
                    )
                )
        elif key == "subject" or key.endswith("_subject"):
            if isinstance(child, yaml.ScalarNode) and child.tag.endswith(":str"):
                judged, why = _request_shaped(
                    sibling_keys=keys, parent_key=parent_key, filename=filename
                )
                values.append(
                    Value(
                        kind="yaml-subject",
                        path=rel,
                        line=child.start_mark.line + 1,
                        key=key,
                        value=str(child.value),
                        judged=judged,
                        why=why,
                    )
                )
        if isinstance(child, yaml.MappingNode):
            _walk_mapping(
                child, rel=rel, filename=filename, parent_key=key, values=values
            )
        elif isinstance(child, yaml.SequenceNode):
            for element in child.value:
                if isinstance(element, yaml.MappingNode):
                    _walk_mapping(
                        element,
                        rel=rel,
                        filename=filename,
                        parent_key=key,
                        values=values,
                    )


def scan_yaml(
    path: pathlib.Path, rel: str
) -> tuple[list[Value], list[Unresolved], list[Error]]:
    """Every collected value in one YAML document, and the file if it failed to parse."""
    try:
        documents = list(yaml.compose_all(path.read_text(encoding="utf-8")))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        return [], [], [Error(path=rel, line=1, detail=f"unparsed: {type(exc).__name__}")]
    values: list[Value] = []
    for document in documents:
        if isinstance(document, yaml.MappingNode):
            _walk_mapping(
                document,
                rel=rel,
                filename=path.name,
                parent_key=None,
                values=values,
            )
    return values, [], []


# --- Python ----------------------------------------------------------------


def _callee_name(call: ast.Call) -> str:
    """The simple name of what is being called — `ProductRequest`, `_answer`, ...."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return "<expression>"


def _string_constant(node: ast.expr) -> str | None:
    """The text of a plain string literal, or `None` for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _root_name(node: ast.expr) -> str | None:
    """The `NAME` at the base of `NAME`, `NAME[...]` or `NAME[...][...]`."""
    current = node
    while isinstance(current, ast.Subscript):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def _module_bindings(tree: ast.Module) -> tuple[dict[str, str], frozenset[str]]:
    """Module-level `NAME = "text"` bindings, and the names loaded out of YAML.

    Both are what makes an indirection resolvable. A `subject=SUBJECT` whose
    `SUBJECT` is a module-level literal is folded and judged; a
    `subject=QUESTION["question"]["subject"]` whose `QUESTION` came out of
    `yaml.safe_load` is a value this probe already judges at its YAML source,
    so the position is reported as that rather than as an unknown.
    """
    literals: dict[str, str] = {}
    yaml_backed: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            targets: list[ast.expr] = list(statement.targets)
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            targets = [statement.target]
            value = statement.value
        else:
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if not names:
            continue
        text = _string_constant(value)
        if text is not None:
            for name in names:
                literals[name] = text
            continue
        if any(
            isinstance(inner, ast.Call) and _callee_name(inner) in YAML_LOADERS
            for inner in ast.walk(value)
        ):
            yaml_backed.update(names)
    return literals, frozenset(yaml_backed)


def scan_python(
    path: pathlib.Path, rel: str, kind: str
) -> tuple[list[Value], list[Unresolved], list[Error]]:
    """`subject=` / `parameters=` call keywords and subject-named module bindings."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
        return [], [], [Error(path=rel, line=1, detail=f"unparsed: {type(exc).__name__}")]
    literals, yaml_backed = _module_bindings(tree)
    values: list[Value] = []
    unresolved: list[Unresolved] = []

    def _record(*, callee: str, name: str, node: ast.expr, suffix: str) -> None:
        """One `subject=`/`parameters=` position, folded where the source allows."""
        judged = callee == REQUEST_CALLEE
        why = (
            f"callee is {REQUEST_CALLEE}"
            if judged
            else f"callee is {callee}, not {REQUEST_CALLEE}"
        )
        text = _string_constant(node)
        if text is not None:
            values.append(
                Value(
                    kind=f"{kind}-{suffix}",
                    path=rel,
                    line=node.lineno,
                    key=f"{callee}({name}=)",
                    value=text,
                    judged=judged,
                    why=f"a source literal; {why}",
                )
            )
            return
        root = _root_name(node)
        if isinstance(node, ast.Name) and node.id in literals:
            values.append(
                Value(
                    kind=f"{kind}-{suffix}",
                    path=rel,
                    line=node.lineno,
                    key=f"{callee}({name}={node.id})",
                    value=literals[node.id],
                    judged=judged,
                    why=f"folded from the module binding {node.id}; {why}",
                )
            )
            return
        if isinstance(node, ast.Constant):
            unresolved.append(
                Unresolved(
                    cls=NOT_A_STRING,
                    path=rel,
                    line=node.lineno,
                    detail=f"{callee}({name}=) holds {node.value!r}",
                    why=(
                        f"a {type(node.value).__name__}, not a string —"
                        " refuse_floor walks declared string positions only"
                    ),
                )
            )
            return
        if root is not None and root in yaml_backed:
            unresolved.append(
                Unresolved(
                    cls=UNRESOLVED,
                    path=rel,
                    line=node.lineno,
                    detail=f"{callee}({name}={ast.unparse(node)})",
                    why=(
                        f"{root} is a parsed YAML document — the value is judged"
                        " at its YAML source above, not here"
                    ),
                )
            )
            return
        unresolved.append(
            Unresolved(
                cls=UNRESOLVED,
                path=rel,
                line=node.lineno,
                detail=f"{callee}({name}=) is {type(node).__name__}",
                why=(
                    "not a literal and not bound to one in this module — a"
                    " fixture, a parameter or an estate-resolved value"
                ),
            )
        )

    def _record_parameter(*, callee: str, name: str, node: ast.expr) -> None:
        """A `parameters=` mapping value, descending through nested containers.

        A declared `object` member and a declared `array` element are both
        positions `refuse_floor` walks (its `_refuse_floor_below` mirrors
        `refuse_payload`'s traversal), so a literal nested inside a dict or a
        list in the source is collected rather than reported as unknown.
        """
        if isinstance(node, ast.Dict):
            for element in node.values:
                _record_parameter(callee=callee, name=name, node=element)
            return
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for element in node.elts:
                _record_parameter(callee=callee, name=name, node=element)
            return
        _record(callee=callee, name=name, node=node, suffix="parameter-kwarg")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            wanted = [n for n in names if n.upper().endswith(SUBJECT_NAME_SUFFIXES)]
            text = _string_constant(node.value) if node.value is not None else None
            if wanted and text is not None:
                values.append(
                    Value(
                        kind=f"{kind}-binding",
                        path=rel,
                        line=node.lineno,
                        key=wanted[0],
                        value=text,
                        judged=True,
                        why="a subject-named module binding in an example module",
                    )
                )
            continue
        if not isinstance(node, ast.Call):
            continue
        callee = _callee_name(node)
        for keyword in node.keywords:
            name = keyword.arg
            if name is None:
                continue
            if name == "subject" or name.endswith("_subject"):
                _record(
                    callee=callee,
                    name=name,
                    node=keyword.value,
                    suffix="subject-kwarg",
                )
            elif name == PARAMETERS_KEY and isinstance(keyword.value, ast.Dict):
                _record_parameter(callee=callee, name=name, node=keyword.value)
    return values, unresolved, []


# --- the controls ----------------------------------------------------------


def positive_control() -> tuple[list[str], list[str]]:
    """Run the matcher over values it MUST refuse, and one it must admit.

    Returns `(fired, missed)`. `missed` non-empty means the instrument cannot
    produce the verdict it is reporting the absence of, and the run fails —
    a zero from a matcher that never refuses is indistinguishable from a zero
    from a glob that stopped matching.
    """
    outside = (
        ("single-quote splice", "o'brien"),
        ("double-quote splice", 'x" OR "1"="1'),
        ("angle bracket", "<script>"),
        ("leading hyphen", "-leading-hyphen"),
        ("over the length bound", "A" * 513),
    )
    inside = ("built from the allowlist", "A0z:/._~@+=-")
    fired: list[str] = []
    missed: list[str] = []
    for label, text in outside:
        if SUBJECT_FLOOR_V1.fullmatch(text) is None:
            fired.append(f"{label}: REFUSED as required ({len(text)} chars)")
        else:
            missed.append(f"{label}: ADMITTED — the matcher cannot refuse")
    label, text = inside
    if SUBJECT_FLOOR_V1.fullmatch(text) is not None:
        fired.append(f"{label}: admitted as required ({text!r})")
    else:
        missed.append(f"{label}: REFUSED — the matcher refuses everything")
    return fired, missed


def iter_source_files(root: pathlib.Path, glob: str) -> list[pathlib.Path]:
    """Files one source glob matches, skipping build and VCS noise."""
    return sorted(
        path
        for path in root.glob(glob)
        if path.is_file() and not any(part in SKIP_DIRS for part in path.parts)
    )


# --- the report ------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Print the population, the verdicts and the controls; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent.parent,
        help="repository root to scan (default: the tree this file lives in)",
    )
    args = parser.parse_args(argv)
    root: pathlib.Path = args.root.resolve()

    print(f"probe_subject_floor — {SUBJECT_FLOOR_VERSION} = {SUBJECT_FLOOR_V1.pattern}")
    print(f"root: {root}")
    estate = sorted(name for name in os.environ if name.startswith(ESTATE_PREFIX))
    print(
        f"mode: LITERAL ONLY. {len(estate)} {ESTATE_PREFIX}* variables are set"
        f" ({', '.join(estate) if estate else 'none'}); this probe resolves no"
        " estate subject under any setting — it opens no socket. Estate-resolved"
        " subjects are DON'T KNOW here and are covered by the wave's"
        " estate-gated example run."
    )
    print()

    print("=== population ===")
    values: list[Value] = []
    residual: list[Unresolved] = []
    errors: list[Error] = []
    empty: list[str] = []
    for kind, glob in SOURCES:
        files = iter_source_files(root, glob)
        if not files:
            empty.append(glob)
        found: list[Value] = []
        unknown: list[Unresolved] = []
        for path in files:
            rel = path.relative_to(root).as_posix()
            if path.suffix in {".yaml", ".yml"}:
                got, open_ended, bad = scan_yaml(path, rel)
            else:
                got, open_ended, bad = scan_python(path, rel, kind)
            found.extend(got)
            unknown.extend(open_ended)
            errors.extend(bad)
        values.extend(found)
        residual.extend(unknown)
        judged = sum(1 for v in found if v.judged)
        print(
            f"  {kind:22s} {glob:24s} files={len(files):4d}"
            f" values={len(found):4d} judged={judged:4d}"
            f" not-judged={len(found) - judged:4d}"
            f" unresolved={len(unknown):4d}"
        )
    by_key_kind: dict[str, int] = {}
    for value in values:
        by_key_kind[value.kind] = by_key_kind.get(value.kind, 0) + 1
    print("  by value class:")
    for name in sorted(by_key_kind):
        print(f"    {name:34s} {by_key_kind[name]:4d}")
    callees: dict[str, int] = {}
    for value in values:
        if "(" in value.key:
            callees[value.key.split("(", 1)[0]] = (
                callees.get(value.key.split("(", 1)[0], 0) + 1
            )
    print("  by Python callee holding a collected keyword:")
    for name in sorted(callees):
        print(f"    {name:34s} {callees[name]:4d}")
    print()

    judged_values = [v for v in values if v.judged]
    findings = [v for v in judged_values if v.refuses]
    classified = [v for v in values if not v.judged and v.refuses]
    passed = [v for v in values if not v.refuses]

    print("=== every judged value, with its verdict ===")
    for value in sorted(judged_values, key=lambda v: (v.path, v.line, v.key)):
        print(value.line_out())
    print()

    print("=== refusals at positions refuse_floor JUDGES — these are findings ===")
    if findings:
        for value in findings:
            print(value.line_out())
            print(f"      classified judged because: {value.why}")
    else:
        print("  none")
    print()

    print(
        "=== refusals at positions refuse_floor does NOT judge — not findings,"
        " and the classification below is the author's ==="
    )
    if classified:
        for value in sorted(classified, key=lambda v: (v.path, v.line, v.key)):
            print(value.line_out())
            print(f"      classified not-judged because: {value.why}")
    else:
        print("  none")
    print()

    unknown_values = [u for u in residual if u.cls == UNRESOLVED]
    non_strings = [u for u in residual if u.cls == NOT_A_STRING]

    print(
        "=== UNRESOLVED residual: positions whose value is not in the source."
        " Never a pass; this is what this probe does not know ==="
    )
    if unknown_values:
        for item in sorted(unknown_values, key=lambda u: (u.path, u.line)):
            print(item.line_out())
    else:
        print("  none")
    print()

    print(
        "=== not a string: fully known, and outside what refuse_floor judges ==="
    )
    if non_strings:
        for item in sorted(non_strings, key=lambda u: (u.path, u.line)):
            print(item.line_out())
    else:
        print("  none")
    print()

    print("=== files the probe could not parse at all — instrument errors ===")
    if errors:
        for error in sorted(errors, key=lambda e: (e.path, e.line)):
            print(error.line_out())
    else:
        print("  none")
    print()

    print("=== positive control: can this matcher refuse at all? ===")
    fired, missed = positive_control()
    for line in fired:
        print(f"  FIRED  {line}")
    for line in missed:
        print(f"  MISSED {line}")
    print()

    print("=== counts ===")
    print(
        f"  passed={len(passed)} failed={len(findings)}"
        f" errors={len(errors)} skipped={len(classified) + len(non_strings)}"
        f" unresolved={len(unknown_values)}"
    )
    print("  legend:")
    print("    passed     — the value lies inside the floor")
    print("    failed     — outside the floor at a position refuse_floor judges")
    print("    errors     — a file the probe could not parse at all")
    print(
        f"    skipped    — {len(classified)} outside the floor at a position"
        f" refuse_floor does not judge, plus {len(non_strings)} not a string at"
        " all; skipped from the finding count, never from the report"
    )
    print(
        "    unresolved — a position whose value is not in the source (a"
        " fixture, a parameter, an estate-resolved value); a residual, not a"
        " pass, and listed above in full"
    )
    print()

    untrustworthy: list[str] = []
    if empty:
        untrustworthy.append(
            f"source glob(s) matched no files: {', '.join(empty)}"
        )
    if missed:
        untrustworthy.append(f"positive control did not fire: {len(missed)} of 6")
    if errors:
        untrustworthy.append(f"{len(errors)} file(s) the probe could not parse")
    if untrustworthy:
        print("VERDICT: COULD-NOT-TELL — this probe's zero means nothing because:")
        for reason in untrustworthy:
            print(f"  - {reason}")
        return 2
    if findings:
        print(
            f"VERDICT: REFUSED — {len(findings)} value(s) the example suite"
            f" carries lie outside {SUBJECT_FLOOR_VERSION} at a position"
            " refuse_floor judges. Each is named above."
        )
        return 1
    print(
        "VERDICT: PASS — every literal subject and declared string parameter the"
        " example suite carries at a position refuse_floor judges lies inside"
        f" {SUBJECT_FLOOR_VERSION}; the population above is non-empty; the"
        " matcher demonstrated it can refuse."
    )
    print(
        f"  Residual, stated: {len(unknown_values)} position(s) whose value is"
        " not in the source, and the whole of the estate-resolved population."
        " This probe does not cover those."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - the command-line entry point
    sys.exit(main())
