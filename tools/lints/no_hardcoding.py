"""CINV-01 — the No-Hardcoding Rule (CLAUDE.md §6.4).

"Code contains interpreters and factories, never the things interpreted."
Three heuristics, one AST walk, plus the D-08 allowlist:

``cinv01a-prompt-shape``
    A string constant that looks like a prompt or system instruction. Scored
    against four signals; two are enough. Docstrings are excluded by *position*
    (the first ``Expr`` of a module/class/function body), never by content, and
    obvious non-prose (SQL, URIs, single tokens) is filtered before scoring —
    SQL is the main false-positive class (04-RESEARCH.md Pitfall 1).

``cinv01b-numeric-table``
    A module-level dict/list/tuple/set constant whose values are predominantly
    numeric — a half-life table, a threshold band, a routing weight map. These
    are Control Plane values, not code. Also fires on a numeric default for a
    declared parameter field in a parameter-schema module (D-IMPL-38: no silent
    defaults).

``cinv01c-factory-bypass``
    ``Agent(...)`` / ``Task(...)`` construction outside a factory module —
    "factory module" being an explicit allowlist of exact paths
    (``FACTORY_MODULE_ALLOWLIST``), never a naming convention (WR-06). Also
    tracks simple module-level aliasing (``A = Agent; A(...)``) and import
    aliasing (``from ... import Agent as A; A(...)``), so a
    one-line rename is not a silent hole in the rule. The accepted residual
    (D-12, Dave's explicit ruling) is *dynamic* construction — ``getattr``,
    ``globals()``, importlib — which no static check can see; the lint is the
    mechanism of record and no runtime construction token exists.

Unlike the import rules, CINV-01 has legitimate exceptions, so it takes an
allowlist: ``tools/lints/allowlist.yaml``, entries of
``{file, rule, fingerprint, reason, reviewer}`` matched exactly on all three of
file+rule+fingerprint. The fingerprint is the sha256 of the offending literal,
so an exception silently stops applying the moment the literal drifts — the
reviewer signed off on *that* text, not on that line number.
"""

from __future__ import annotations

import ast
import hashlib
import pathlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import yaml

from tools.lints import format_finding, read_tree

RULE_PROMPT_SHAPE = "cinv01a-prompt-shape"
RULE_NUMERIC_TABLE = "cinv01b-numeric-table"
RULE_FACTORY_BYPASS = "cinv01c-factory-bypass"

ALLOWLIST_PATH = pathlib.Path(__file__).with_name("allowlist.yaml")

#: Marker appended to every CINV-01 finding so the allowlist can key off the
#: exact literal rather than a line number.
_FP_RE = re.compile(r"\[fp=([0-9a-f]{64})\]")

# --- CINV-01a tuning knobs -------------------------------------------------

#: Below this length a string cannot plausibly be a prompt; skip scoring.
MIN_PROMPT_CHARS = 40
#: Signal (d): prose length.
PROSE_CHARS = 200
#: Signal (a): sentence count.
MIN_SENTENCES = 3
#: Signal (c): template-brace density.
MIN_BRACES = 3
#: Signal (b): role-preamble openers.
ROLE_OPENERS: tuple[str, ...] = ("you are", "always", "never", "respond")
#: Number of signals required to flag.
PROMPT_SCORE_THRESHOLD = 2

_SQL_OPENERS = ("select", "insert", "update", "delete", "create", "with", "alter")
_SENTENCE_RE = re.compile(r"[.!?](?:\s|$)")

#: Modules whose declared-parameter fields must carry no numeric default.
PARAM_SCHEMA_MARKERS: tuple[str, ...] = ("params", "parameters", "thresholds")

#: Construction of these names must go through a factory module. ``Workflow``
#: joined in 07-04: ORCH-01's "via the Task Factory" is literal, extended one
#: level — the engine accepts only WorkflowFactory-built handles.
FACTORY_ONLY_NAMES: frozenset[str] = frozenset({"Agent", "Task", "Workflow"})

#: The exact factory modules exempt from CINV-01c — an explicit allowlist,
#: never a naming convention (WR-06). A module earns exemption by *being* one
#: of the shipped factories, not by putting "factory" somewhere in its path;
#: the entries are the repo-relative file path and its dotted module form.
FACTORY_MODULE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "src/ccf/agents/factory.py",
        "ccf.agents.factory",
        "src/ccf/workflow/factory.py",
        "ccf.workflow.factory",
    }
)


def _is_factory_module(path: pathlib.Path, module_name: str) -> bool:
    """Whether ``path``/``module_name`` names an allowlisted factory module.

    Matches the dotted module name exactly, or the file path exactly /
    suffix-anchored at a path-segment boundary (so an absolute path to the
    real factory file matches, but ``my_factory_helpers.py`` or a
    ``factories/`` directory cannot earn exemption by naming — WR-06).
    """
    if module_name in FACTORY_MODULE_ALLOWLIST:
        return True
    posix = path.as_posix()
    return any(
        posix == entry or posix.endswith("/" + entry)
        for entry in FACTORY_MODULE_ALLOWLIST
        if "/" in entry
    )


def fingerprint(literal: str) -> str:
    """sha256 hex digest of the exact literal an allowlist entry exempts."""
    return hashlib.sha256(literal.encode("utf-8")).hexdigest()


# --- D-08 allowlist --------------------------------------------------------


@dataclass(frozen=True)
class AllowlistEntry:
    """One reviewed, git-versioned CINV-01 exception."""

    file: str
    rule: str
    fingerprint: str
    reason: str
    reviewer: str

    def matches(self, file: str, rule: str, fp: str) -> bool:
        return self.file == file and self.rule == rule and self.fingerprint == fp


@dataclass(frozen=True)
class Allowlist:
    """The set of reviewed exceptions in force."""

    entries: list[AllowlistEntry] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: Sequence[Any] | None) -> "Allowlist":
        """Build from parsed YAML, rejecting entries missing a required field.

        An exception without a reason and a named reviewer is exactly the
        repudiation risk the allowlist exists to close (threat T-04-03).
        """
        entries: list[AllowlistEntry] = []
        for index, item in enumerate(raw or []):
            if not isinstance(item, dict):
                raise ValueError(f"allowlist entry {index} is not a mapping")
            missing = [
                key
                for key in ("file", "rule", "fingerprint", "reason", "reviewer")
                if not item.get(key)
            ]
            if missing:
                raise ValueError(
                    f"allowlist entry {index} is missing required field(s):"
                    f" {', '.join(missing)}"
                )
            entries.append(
                AllowlistEntry(
                    file=str(item["file"]),
                    rule=str(item["rule"]),
                    fingerprint=str(item["fingerprint"]),
                    reason=str(item["reason"]),
                    reviewer=str(item["reviewer"]),
                )
            )
        return cls(entries)

    def allows(self, file: str, rule: str, fp: str) -> bool:
        return any(entry.matches(file, rule, fp) for entry in self.entries)


def load_allowlist(path: pathlib.Path | None = None) -> Allowlist:
    """Load the versioned allowlist (defaults to `tools/lints/allowlist.yaml`)."""
    target = path or ALLOWLIST_PATH
    if not target.exists():
        return Allowlist([])
    document = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError(f"{target}: expected a mapping with an 'entries' key")
    return Allowlist.from_raw(document.get("entries") or [])


def apply_allowlist(findings: Iterable[str], allowlist: Allowlist) -> list[str]:
    """Drop findings covered by an exact file+rule+fingerprint allowlist entry."""
    kept: list[str] = []
    for finding in findings:
        parts = finding.split(" ", 2)
        file = parts[0].rsplit(":", 1)[0]
        rule = parts[1] if len(parts) > 1 else ""
        match = _FP_RE.search(finding)
        if match and allowlist.allows(file, rule, match.group(1)):
            continue
        kept.append(finding)
    return kept


# --- heuristics ------------------------------------------------------------


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """ids() of the Constant nodes that occupy a docstring position."""
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            docstrings.add(id(body[0].value))
    return docstrings


def _is_prose_candidate(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < MIN_PROMPT_CHARS:
        return False
    if " " not in stripped:  # paths, URIs, identifiers
        return False
    if "://" in stripped:
        return False
    if stripped.split(" ", 1)[0].lower().rstrip("(") in _SQL_OPENERS:
        return False
    return True


def prompt_score(text: str) -> int:
    """Count the prompt-shape signals `text` exhibits (0-4)."""
    lowered = text.strip().lower()
    score = 0
    if len(_SENTENCE_RE.findall(text)) >= MIN_SENTENCES:
        score += 1
    if any(lowered.startswith(opener) for opener in ROLE_OPENERS):
        score += 1
    if text.count("{") >= MIN_BRACES:
        score += 1
    if len(text) > PROSE_CHARS:
        score += 1
    return score


def _is_numeric_constant(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ) or (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.UAdd, ast.USub))
        and _is_numeric_constant(node.operand)
    )


def _numeric_table_values(node: ast.expr) -> list[ast.expr] | None:
    """Element values of a literal collection, or None if it is not one."""
    if isinstance(node, ast.Dict):
        return [v for v in node.values if v is not None]
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return list(node.elts)
    return None


def _is_numeric_table(node: ast.expr) -> bool:
    values = _numeric_table_values(node)
    if values is None or len(values) < 2:
        return False
    numeric = sum(1 for value in values if _is_numeric_constant(value))
    return numeric * 2 > len(values)


def _is_param_schema_module(path: pathlib.Path, module_name: str) -> bool:
    haystack = f"{path.as_posix()} {module_name}".lower()
    return any(marker in haystack for marker in PARAM_SCHEMA_MARKERS)


def _called_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


# --- entrypoints -----------------------------------------------------------


def check_source(source: str, path: pathlib.Path, module_name: str) -> list[str]:
    """Check already-read `source` attributed to `path` / `module_name`."""
    tree = read_tree(source, path)
    findings: list[str] = []
    docstrings = _docstring_nodes(tree)
    in_factory_module = _is_factory_module(path, module_name)
    param_schema = _is_param_schema_module(path, module_name)

    def emit(node: ast.AST, rule: str, message: str, literal: str) -> None:
        findings.append(
            format_finding(
                path,
                getattr(node, "lineno", 0),
                rule,
                f"{message} [fp={fingerprint(literal)}]",
            )
        )

    # CINV-01a — prompt-shaped literals anywhere in the module.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        text = node.value
        if not _is_prose_candidate(text):
            continue
        if prompt_score(text) >= PROMPT_SCORE_THRESHOLD:
            emit(
                node,
                RULE_PROMPT_SHAPE,
                "prompt-shaped string literal in code — prompts are versioned"
                " artifacts referenced by URI (CLAUDE.md §6.4)",
                text,
            )

    # CINV-01b — module-level numeric tables.
    for node in tree.body:
        if isinstance(node, ast.Assign) and _is_numeric_table(node.value):
            emit(
                node,
                RULE_NUMERIC_TABLE,
                "module-level numeric table in code — half-lives, thresholds and"
                " weights are Control Plane values (CLAUDE.md §6.4, §11)",
                ast.unparse(node),
            )
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and _is_numeric_table(node.value)
        ):
            emit(
                node,
                RULE_NUMERIC_TABLE,
                "module-level numeric table in code — half-lives, thresholds and"
                " weights are Control Plane values (CLAUDE.md §6.4, §11)",
                ast.unparse(node),
            )

    # CINV-01b (cont.) — numeric defaults on declared parameter fields.
    if param_schema:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for stmt in node.body:
                if (
                    isinstance(stmt, ast.AnnAssign)
                    and stmt.value is not None
                    and _is_numeric_constant(stmt.value)
                ):
                    emit(
                        stmt,
                        RULE_NUMERIC_TABLE,
                        "numeric default on a declared parameter field — a missing"
                        " value is a registration failure, not a fallback"
                        " (D-IMPL-38, no silent defaults)",
                        ast.unparse(stmt),
                    )

    # CINV-01c — factory bypass. Aliases of factory-only names join the
    # checked set so a rename is never a silent hole: bare-name assignment
    # (`A = Agent`), attribute assignment (`A = module.Agent` — WR-04), and
    # import aliases (`from x import Agent as A`, `import x as A` where x
    # names a factory-only name — WR-06). Every *static* rename is covered;
    # dynamic construction (a name resolved at runtime, e.g. through getattr)
    # stays the D-12 accepted residual, which is the whole point of the
    # distinction — a one-line static rename must not escape.
    if not in_factory_module:
        checked_names = set(FACTORY_ONLY_NAMES)
        aliases: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and (
                (
                    isinstance(node.value, ast.Name)
                    and node.value.id in FACTORY_ONLY_NAMES
                )
                or (
                    isinstance(node.value, ast.Attribute)
                    and node.value.attr in FACTORY_ONLY_NAMES
                )
            ):
                canonical_name = (
                    node.value.id
                    if isinstance(node.value, ast.Name)
                    else node.value.attr
                )
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        checked_names.add(target.id)
                        aliases[target.id] = canonical_name
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for imported in node.names:
                    basename = imported.name.rsplit(".", 1)[-1]
                    if basename in FACTORY_ONLY_NAMES and imported.asname:
                        checked_names.add(imported.asname)
                        aliases[imported.asname] = basename
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _called_name(node.func) in (
                checked_names
            ):
                called = _called_name(node.func)
                assert called is not None
                canonical = aliases.get(called, called)
                emit(
                    node,
                    RULE_FACTORY_BYPASS,
                    f"{canonical} construction outside a factory"
                    " module — agents and tasks come from the Agent & Task"
                    " Factory reading definition artifacts (CLAUDE.md §6.4)",
                    ast.unparse(node),
                )

    findings.sort(key=lambda f: (int(f.split(":", 1)[1].split(" ", 1)[0]), f))
    return findings


def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
