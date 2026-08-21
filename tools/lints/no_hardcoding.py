"""CINV-01 — the No-Hardcoding Rule (CLAUDE.md §6.4).

"Code contains interpreters and factories, never the things interpreted."
Three heuristics, one AST walk, plus the D-08 allowlist:

``cinv01a-prompt-shape``
    A string constant that looks like a prompt or system instruction. Scored
    against four signals; two are enough. Docstrings are excluded by *position*
    (the first ``Expr`` of a module/class/function body), never by content, and
    obvious non-prose (SQL, URIs, single tokens) is filtered before scoring —
    SQL is the main false-positive class (04-RESEARCH.md Pitfall 1).

    **Developer-facing diagnostics are excluded structurally** (Dave,
    2026-08-04; plan 15-04). *A prompt is a string sent to a model; a
    diagnostic is a string shown to a developer.* The scoring signals detect
    "long English string literal", which is a proxy for the wrong thing: it
    cannot tell a system instruction from a multi-sentence CI failure message
    naming its own fix — and this repo's conventions actively encourage the
    latter (15-01 ships a test asserting a drift message names the command
    that regenerates the artifact). Rather than allowlisting each such
    message, :func:`is_developer_diagnostic` separates the two categories on
    the distinction itself: a literal that carries developer-toolchain
    markers (a backticked command, a repo-relative filename, a ``callable()``
    reference) and does **not** address a reader is a diagnostic, and is not
    scored. The exemption is this rule, not an allowlist entry, so every
    future diagnostic message inherits it.

    **A SECOND ARM, BY DESTINATION** (Dave, ruling 6(b), Phase 20). The rule
    also refuses a prose-candidate literal that reaches a *model-instruction
    sink* — :data:`INSTRUCTION_SINK_KWARGS`, :data:`INSTRUCTION_SINK_CALLS`,
    or a :data:`MESSAGE_CONTENT_KEYS` value of a mapping that also carries a
    ``role`` key — **without consulting** :func:`prompt_score` at all. This is
    the discriminator the paragraph above already commits to in words,
    implemented by destination rather than by shape, and it exists because the
    shape signals cannot see a short agent prompt: the four realistic
    agent-prompt shapes measured at Phase 20's plan gate score 0-1 against a
    threshold of 2. Lowering :data:`PROMPT_SCORE_THRESHOLD` to 1 was measured
    over all four trees at **94 new findings**, effectively all false, and
    would still have missed two of the four shapes. The destination arm was
    measured at **2 findings, both genuine** — the same hardcoded agent
    instruction in two external-example clients, remediated in the plan that
    added the arm rather than allowlisted. The value is FOLLOWED to the sink:
    through a name bound anywhere in the module, through an f-string's
    constant parts, and through the default of an ``os.environ.get(NAME, …)``
    read, which is what a prompt wearing an env var as a hat looks like.

    *Accepted residual, stated because a name-keyed sink set has one.* The
    sink sets are enumerations of names, so a harness whose instruction API
    uses a name outside them escapes the arm. This is the same class of
    residual as ``D-12``'s dynamic-construction hole in ``cinv01c`` and is
    accepted on the same ground: every *static* spelling the three shipped
    harnesses use is covered, and the sink sets are module constants so adding
    a fourth harness is a one-line edit beside a test. The arm is the
    mechanism of record; it is not a proof of absence.

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

# --- CINV-01a: prompt vs developer diagnostic ------------------------------
#
# Dave's ruling, 2026-08-04 (plan 15-03 Task 4 checkpoint; implemented in
# 15-04): the two prose-diagnostic false positives the widened lint surfaced
# are resolved by refining this rule, NOT by allowlist entries. The rule's
# job is to separate two categories that the scoring signals conflate.

#: A backticked span — how this repo quotes a command a developer should run
#: (``Run `make openapi` and commit the result``).
_BACKTICK_SPAN_RE = re.compile(r"`[^`\n]{2,120}`")
#: A repo-relative filename or path. A prompt names entities and policies; a
#: diagnostic names the file that is wrong and the artifact that fixes it.
_REPO_PATH_RE = re.compile(
    r"\b[\w./-]*\w\.(?:py|json|ya?ml|toml|md|cfg|ini|txt|lock|sh|proto)\b"
)
#: A zero-argument callable reference (``create_app()``) — source vocabulary,
#: not natural language a model is asked to follow.
_CALLABLE_REF_RE = re.compile(r"\b[A-Za-z_]\w*\(\)")

#: Any one of these makes a literal *developer-facing*. Kept as a tuple so the
#: discriminator is enumerable and testable rather than buried in a boolean.
DIAGNOSTIC_MARKERS: tuple[re.Pattern[str], ...] = (
    _BACKTICK_SPAN_RE,
    _REPO_PATH_RE,
    _CALLABLE_REF_RE,
)

#: Second-person address. Prompts talk *to* a reader ("you are", "your
#: answer"); diagnostics describe state ("the committed spec no longer
#: matches"). Deliberately asymmetric: a message that both names a `make`
#: target and addresses a reader is still scored, because the cost of a
#: false positive (reword, or a reviewed allowlist entry) is lower than the
#: cost of a prompt slipping through behind a filename.
_SECOND_PERSON_RE = re.compile(r"\byou(?:r|'re|'ve)?\b", re.IGNORECASE)

# --- CINV-01a: the destination arm (Dave, ruling 6(b), Phase 20) -----------
#
# A prompt is refused by WHERE IT GOES, not by how long it is. The three sets
# below are the sink surface, kept as module constants beside the tuning knobs
# so it is a config surface a reader can enumerate rather than a literal buried
# in a walk. Each name is here because a shipped harness spells its instruction
# API that way.

#: Keyword arguments that carry a model instruction.
#:
#: * ``system`` / ``system_prompt`` / ``system_instruction`` — the Anthropic,
#:   Claude-Agent-SDK and Google-GenAI spellings of the system turn.
#: * ``instruction`` / ``instructions`` — ADK's ``LlmAgent(instruction=…)`` and
#:   the OpenAI Assistants spelling.
#: * ``prompt`` / ``user_prompt`` / ``preamble`` / ``persona`` — the generic
#:   spellings a bespoke loop reaches for.
#: * ``text`` — ``google.genai.types.Part(text=…)``, which is the sink one of
#:   the two real violations this arm surfaced actually lands in.
#: * ``content`` — the message-body spelling, as a keyword rather than inside a
#:   mapping.
INSTRUCTION_SINK_KWARGS: frozenset[str] = frozenset(
    {
        "system",
        "system_prompt",
        "system_instruction",
        "instruction",
        "instructions",
        "prompt",
        "user_prompt",
        "preamble",
        "persona",
        "text",
        "content",
    }
)

#: Call names whose FIRST POSITIONAL argument is the instruction. Matched on
#: the attribute name alone, so the receiver does not have to be resolvable —
#: ``ClaudeSDKClient.query(prompt)``, the sink Phase 20's leg 2 uses, is why
#: ``query`` is here. That name is also a SQL idiom, and the collision is
#: harmless only because :func:`_is_prose_candidate` filters SQL first; see
#: ``CONTROL 8``.
INSTRUCTION_SINK_CALLS: frozenset[str] = frozenset(
    {"query", "send_message", "create_message", "complete", "generate", "ask"}
)

#: The value positions of a chat-message mapping, recognised **only when the
#: same mapping also carries a ``role`` key**. The ``role`` requirement is what
#: keeps this from firing on every dict with a ``content`` field, and it is
#: asserted in both directions by ``CONTROL 7``.
MESSAGE_CONTENT_KEYS: tuple[str, ...] = ("content", "text")

#: Bound on binding-chain resolution (``a = "…"; b = a; sink(b)``). Finite so a
#: cyclic assignment cannot hang the lint.
_MAX_RESOLUTION_DEPTH = 8

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
        # `file` is the path exactly as the lint reported it — absolute when
        # the runner's --base is absolute (the default: cwd). Entries are
        # repo-relative per the allowlist header, so match exactly or
        # suffix-anchored at a path-segment boundary (same discipline as
        # `_is_factory_module`; the fingerprint keeps the match exact on the
        # offending literal either way).
        return (
            self.rule == rule
            and self.fingerprint == fp
            and (self.file == file or file.endswith("/" + self.file))
        )


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


def addresses_a_reader(text: str) -> bool:
    """Whether `text` is written *to* someone — the mark of an instruction.

    Three ways a literal addresses a reader: a role-preamble opener ("You
    are…", "Always…"), second-person pronouns anywhere in the body, or
    template-brace density at or above :data:`MIN_BRACES` (a filled-in
    prompt template). Any one of them keeps the literal in scoring even if it
    also carries developer-toolchain markers.
    """
    lowered = text.strip().lower()
    if any(lowered.startswith(opener) for opener in ROLE_OPENERS):
        return True
    if text.count("{") >= MIN_BRACES:
        return True
    return bool(_SECOND_PERSON_RE.search(text))


def is_developer_diagnostic(text: str) -> bool:
    """Whether `text` is a message shown to a developer, not sent to a model.

    The discriminator Dave's 2026-08-04 ruling asked for: a prompt is a
    string sent to a model, a diagnostic is a string shown to a developer,
    and the difference is mechanically detectable. A literal qualifies when
    it carries at least one :data:`DIAGNOSTIC_MARKERS` signal — a backticked
    command, a repo-relative filename, a ``callable()`` reference — and does
    not :func:`addresses_a_reader`.

    Both halves are load-bearing. Without the markers, any impersonal prose
    would escape; without the reader test, a prompt would escape by
    mentioning a filename.
    """
    if addresses_a_reader(text):
        return False
    return any(pattern.search(text) for pattern in DIAGNOSTIC_MARKERS)


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


# --- CINV-01a destination arm: resolution ----------------------------------


def _is_environment_read(node: ast.Call) -> bool:
    """Whether ``node`` is ``os.environ.get(...)`` or ``os.getenv(...)``.

    Both spellings, and both with or without the ``os.`` prefix, because a
    module doing ``from os import environ, getenv`` is the same read. The
    SECOND argument of such a call is a *default*, and a prompt supplied as a
    default is what actually runs on the default path — an env var worn as a
    hat, which is the exact shape ruling 6(a) forbids.
    """
    name = _called_name(node.func)
    if name == "getenv":
        return True
    if name != "get" or not isinstance(node.func, ast.Attribute):
        return False
    receiver = node.func.value
    if isinstance(receiver, ast.Name):
        return receiver.id == "environ"
    return isinstance(receiver, ast.Attribute) and receiver.attr == "environ"


def _literal_bindings(tree: ast.Module) -> dict[str, ast.expr]:
    """Every ``name = <expr>`` in the module, at ANY depth, flat.

    **Flat rather than scope-aware, deliberately.** A lint that misses a prompt
    because it was assigned inside a function is worse than one that
    occasionally resolves a shadowed name, and the failure modes are not
    symmetric: over-resolution can only ever report a literal that genuinely
    appears in this file, while under-resolution reports a clean tree. Both
    real violations this arm exists for assign inside ``main()``.
    """
    bindings: dict[str, ast.expr] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                bindings[target.id] = node.value
            elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(
                node.value, (ast.Tuple, ast.List)
            ):
                # `PROMPT, MODEL = "…", "…"`. Positional unpack only: a starred
                # target makes the correspondence between names and values
                # ambiguous, and a binding this function is not sure of is worse
                # than one it does not record.
                if not any(
                    isinstance(element, ast.Starred) for element in target.elts
                ) and len(target.elts) == len(node.value.elts):
                    for element, value in zip(target.elts, node.value.elts):
                        if isinstance(element, ast.Name):
                            bindings[element.id] = value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            bindings[node.target.id] = node.value
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            # `if (PROMPT := "…"):` binds exactly like an assignment, and the
            # docstring above claimed to cover "every `name = <expr>`" while
            # this spelling escaped.
            bindings[node.target.id] = node.value
    return bindings


def resolved_text(
    node: ast.expr, bindings: dict[str, ast.expr], depth: int = 0
) -> str | None:
    """The string ``node`` carries at a sink, or ``None``.

    Four ways a value reaches a sink and is still a literal in this file:

    * directly, as a ``str`` constant;
    * through a name bound anywhere in the module (:func:`_literal_bindings`);
    * as an f-string — the constant parts are joined, because an instruction
      with the question interpolated into it is still a hardcoded instruction;
    * as the *default* of an environment read (:func:`_is_environment_read`).

    Anything else resolves to ``None`` and is not reported: this arm reports
    literals that are in the file, never values it could not see.
    """
    if depth > _MAX_RESOLUTION_DEPTH:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        bound = bindings.get(node.id)
        return None if bound is None else resolved_text(bound, bindings, depth + 1)
    if isinstance(node, ast.JoinedStr):
        parts = [
            value.value
            for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        ]
        return "".join(parts) if parts else None
    if isinstance(node, ast.NamedExpr):
        return resolved_text(node.value, bindings, depth + 1)
    if isinstance(node, ast.BoolOp):
        # `os.environ.get("VAR") or "<prompt>"` — the env var worn as a hat,
        # spelled without a default argument at all. The literal is whichever
        # operand carries one.
        return _first_resolved(node.values, bindings, depth)
    if isinstance(node, ast.IfExp):
        return _first_resolved([node.body, node.orelse], bindings, depth)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # A prompt split across a `+` is still one prompt in this file.
        parts = [
            text
            for text in (
                resolved_text(node.left, bindings, depth + 1),
                resolved_text(node.right, bindings, depth + 1),
            )
            if text is not None
        ]
        return "".join(parts) if parts else None
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        bound = bindings.get(node.value.id)
        key = node.slice
        if (
            isinstance(bound, ast.Dict)
            and isinstance(key, ast.Constant)
            and isinstance(key.value, str)
        ):
            for dict_key, dict_value in zip(bound.keys, bound.values):
                if (
                    isinstance(dict_key, ast.Constant)
                    and dict_key.value == key.value
                ):
                    return resolved_text(dict_value, bindings, depth + 1)
        return None
    if isinstance(node, ast.Call):
        if _is_environment_read(node):
            # A default reaches the sink whether it is spelled positionally or
            # as `default=`. Only the DEFAULT is followed: the first argument is
            # the variable's NAME, and resolving that would report the name as
            # if it were the prompt.
            if len(node.args) >= 2:
                return resolved_text(node.args[1], bindings, depth + 1)
            for keyword in node.keywords:
                if keyword.arg == "default":
                    return resolved_text(keyword.value, bindings, depth + 1)
            return None
        # Any other call is treated as a WRAPPER around its content:
        # `"…".strip()`, `textwrap.dedent("…")`, `"…".format(x)`. Resolving
        # through it is deliberately generous, for the reason
        # :func:`_literal_bindings` already states — over-resolution can only
        # ever report a literal that genuinely appears in this file, while
        # under-resolution reports a clean tree. Enumerating wrapper names
        # instead is what left nine escapes open behind one that was fixed.
        candidates: list[ast.expr] = list(node.args)
        if isinstance(node.func, ast.Attribute):
            candidates.insert(0, node.func.value)
        return _first_resolved(candidates, bindings, depth)
    return None


def _first_resolved(
    nodes: Sequence[ast.expr], bindings: dict[str, ast.expr], depth: int
) -> str | None:
    """The first of ``nodes`` that resolves to a literal, or ``None``."""
    for node in nodes:
        text = resolved_text(node, bindings, depth + 1)
        if text is not None:
            return text
    return None


def instruction_sinks(tree: ast.Module) -> list[tuple[ast.expr, str]]:
    """Every ``(argument node, sink description)`` pair in ``tree``.

    Three sink families, each an enumeration of names:

    1. a keyword argument in :data:`INSTRUCTION_SINK_KWARGS`;
    2. the first positional argument of a call named in
       :data:`INSTRUCTION_SINK_CALLS`;
    3. a :data:`MESSAGE_CONTENT_KEYS` value of a mapping that also carries a
       ``role`` key.

    The node returned is the one AT THE SINK, never the literal's definition,
    so a finding sends a reader to where the prompt is used rather than to a
    line that reads as ordinary configuration.
    """
    sinks: list[tuple[ast.expr, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg in INSTRUCTION_SINK_KWARGS:
                    sinks.append((keyword.value, f"{keyword.arg}="))
                elif keyword.arg is None and isinstance(keyword.value, ast.Dict):
                    # `LlmAgent(**{"instruction": "…"})` reaches the same
                    # parameter by the same name; only the spelling differs.
                    for key, value in zip(keyword.value.keys, keyword.value.values):
                        if (
                            isinstance(key, ast.Constant)
                            and isinstance(key.value, str)
                            and key.value in INSTRUCTION_SINK_KWARGS
                        ):
                            sinks.append((value, f'**{{"{key.value}": ...}}'))
            called = _called_name(node.func)
            if called in INSTRUCTION_SINK_CALLS and node.args:
                sinks.append((node.args[0], f"{called}(...)"))
        elif isinstance(node, ast.Dict):
            keys = {
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            if "role" not in keys:
                continue
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and key.value in MESSAGE_CONTENT_KEYS
                ):
                    sinks.append((value, f'{{"role": ..., "{key.value}": ...}}'))
    return sinks


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

    # One literal reported once, whatever caught it. The two CINV-01a arms can
    # both see the same string — a long prompt assigned to a name and then
    # passed to a sink is a score-arm finding at the assignment and a
    # destination-arm finding at the sink — and two findings for one literal is
    # two allowlist entries for one review.
    seen_prompts: set[tuple[int, str]] = set()

    def emit_prompt(node: ast.AST, message: str, literal: str) -> None:
        key = (getattr(node, "lineno", 0), fingerprint(literal))
        if key in seen_prompts:
            return
        seen_prompts.add(key)
        emit(node, RULE_PROMPT_SHAPE, message, literal)

    # CINV-01a, arm 1 (SHAPE) — prompt-shaped literals anywhere in the module.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        text = node.value
        if not _is_prose_candidate(text):
            continue
        if is_developer_diagnostic(text):
            continue
        if prompt_score(text) >= PROMPT_SCORE_THRESHOLD:
            emit_prompt(
                node,
                "prompt-shaped string literal in code — prompts are versioned"
                " artifacts referenced by URI (CLAUDE.md §6.4)",
                text,
            )

    # CINV-01a, arm 2 (DESTINATION) — a prose-candidate literal that reaches a
    # model-instruction sink, whatever its shape. Three deliberate differences
    # from the arm above, each of which is the point rather than an oversight:
    #
    #   * `prompt_score` is NOT consulted. Destination is the whole test. The
    #     four agent-prompt shapes measured at Phase 20's plan gate score 0-1
    #     against a threshold of 2, and lowering that threshold to 1 was
    #     measured at 94 findings — effectively all false — while still missing
    #     two of the four. The signals detect "long English string", which is a
    #     proxy for the wrong thing.
    #   * `is_developer_diagnostic` is NOT consulted. A diagnostic is a string
    #     shown to a developer; a string reaching a model sink is by definition
    #     not that. A literal that carries a backticked command AND is sent to
    #     a model is a prompt.
    #   * `_is_prose_candidate` IS reused, unchanged. `MIN_PROMPT_CHARS = 40` is
    #     the measured knee (40 -> 2, 20 -> 2, 12 -> 15, 1 -> 17 findings over
    #     the rule's four trees), not an inherited default, and its SQL filter
    #     is what makes `query` safe to treat as a sink name.
    bindings = _literal_bindings(tree)
    for sink_node, sink in instruction_sinks(tree):
        if id(sink_node) in docstrings:
            continue
        text = resolved_text(sink_node, bindings)
        if text is None or not _is_prose_candidate(text):
            continue
        emit_prompt(
            sink_node,
            f"string literal reaching a model-instruction sink ({sink}) —"
            " a prompt is refused by where it goes, not by how long it is;"
            " prompts are versioned artifacts referenced by URI"
            " (CLAUDE.md §6.4)",
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
