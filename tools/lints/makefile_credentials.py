"""`makefile-credentials` — no ``make`` recipe may print a credential (SEC-026).

``make`` echoes every recipe line it runs unless that line begins with ``@``,
and it decides that on the **logical** line: backslash continuations are joined
first, so an ``@`` on a continuation's second physical line silences nothing.
A recipe that expands a DSN, URI, URL or password therefore writes it to the
terminal and to the CI log. CLAUDE.md §2.2 says *never a secret in the tree*;
this rule is the same commitment for the build log, and it is the static guard
beside the behavioral exploit test
``tools/lints/tests/test_makefile_credential_echo.py::test_no_credential_bearing_target_prints_its_credential``.

Three refusals, all over the repository-root ``Makefile``:

1. **Echoed expansion.** A joined logical recipe line that expands a
   *credential variable*
   and does not begin with ``@``. A credential variable is one whose name ends
   in ``DSN``, ``URI``, ``URL`` or ``PASSWORD`` — by **name**, whatever today's
   value, so a Fluree ``URL`` with no userinfo is in scope — **or** one whose
   own definition references such a name (one level of indirection, which is
   how ``PG_DSN_ENV`` carries ``CCF_TEST_POSTGRES_DSN``; see
   ``tools/lints/makefile_credentials.py::_indirect_credential_names``).
2. **Printed even behind ``@``.** ``@`` silences make's echo, not the
   command: an ``echo``/``printf`` of a credential variable prints it anyway,
   and ``set -x`` makes the shell echo everything. Both are refused on any
   recipe line. Make's own ``$(info ...)``, ``$(warning ...)`` and
   ``$(error ...)`` print their argument whatever the line's prefix, so a
   credential variable inside one is refused on any line, recipe or not.
3. **Baked credential default.** Any ``=``/``:=``/``?=`` assignment whose
   value carries URL userinfo — ``scheme://user:secret@`` or a colon-less
   ``scheme://token@`` — and any ``*PASSWORD`` variable assigned a literal.

**What a recipe line is.** Every tab-prefixed line is a recipe line, and
nothing on it is exempt because its first word looks like a directive: in rule
context GNU make hands a tab-prefixed ``ifdef``/``export``/``include`` line to
the shell as a command and echoes it like any other (measured: ``t:`` then
``<TAB>ifdef $(DSN)`` prints ``ifdef CANARY`` under ``SHELL=/bin/true``; the
idiom ``<TAB>export X_DSN=$(X_DSN); cmd`` echoes the same way). Directives are
recognized only on non-tab lines, which are read for definitions instead.

Expansions are read in every form make evaluates: ``$(NAME)``, ``${NAME}``,
``$(NAME:a=b)``, ``$(value NAME)``, and ``$(shell printenv NAME)``.

``$$NAME`` is a *shell* reference make does not expand, so rule 1 ignores it —
make echoes the literal ``$NAME``. Rule 2 still refuses an ``echo $$NAME`` of a
credential-named shell variable, because the shell prints that one.

The rule is mechanism, not a deployment value: the four suffixes are the name
class the repository uses for connection material, and the row ruled them
(``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``, SEC-026,
``D-IMPL-368``). Exit code is the gate signal, as for every rule in
``tools/lints/__main__.py``; there is no allowlist (D-13).
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

RULE = "makefile-credentials"

#: The files the rule reads, relative to the base. The repository has one.
MAKEFILES: tuple[str, ...] = ("Makefile",)

#: A make variable name is a credential by name when it ends in one of these.
CREDENTIAL_NAME = re.compile(r"(?:DSN|URI|URL|PASSWORD)$")

#: URL userinfo with a secret part: ``scheme://user:secret@``.
USERINFO = re.compile(r"://[^/@\s]+:[^/@\s]+@")

_ASSIGNMENT = re.compile(
    r"^\s*(?:(?:override|export|private)\s+)*"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_.\-]*)\s*"
    r"(?P<op>\?=|::=|:::=|:=|\+=|!=|=)\s*(?P<value>.*)$"
)
_MAKE_PRINTER = re.compile(r"(?<!\$)\$[({](?:info|warning|error)[ \t]")
_VALUE_REF = re.compile(r"(?<!\$)\$[({]value[ \t]+([A-Za-z_][A-Za-z0-9_.\-]*)[ \t]*[)}]")
_PRINTENV_REF = re.compile(r"(?<!\$)\$[({]shell[ \t]+printenv[ \t]+([A-Za-z_][A-Za-z0-9_]*)")
#: Colon-less userinfo, ``scheme://token@host``.
TOKEN_USERINFO = re.compile(r"://[^/@\s:]+@")
#: A make reference, removed to decide whether a value carries a literal.
_ANY_REF = re.compile(r"\$[({][^)}]*[)}]")
_PRINTER = re.compile(r"(?<![\w.\-/])(?:echo|printf)(?![\w.\-])")
_SET_XTRACE = re.compile(r"\bset\s+(?:-[A-Za-z]*x[A-Za-z]*\b|-o\s+xtrace\b)")
_SHELL_REF = re.compile(r"\$\$\{?([A-Za-z_][A-Za-z0-9_]*)")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*")


@dataclass(frozen=True)
class LogicalLine:
    """One logical Makefile line: continuations joined, first physical line."""

    lineno: int
    text: str
    recipe: bool


def logical_lines(source: str) -> list[LogicalLine]:
    """Join backslash continuations; a line is a recipe line iff its first
    physical line is tab-prefixed (GNU make's recipe prefix)."""
    out: list[LogicalLine] = []
    physical = source.splitlines()
    i = 0
    while i < len(physical):
        start = i
        parts = [physical[i]]
        while parts[-1].endswith("\\") and i + 1 < len(physical):
            parts[-1] = parts[-1][:-1]
            i += 1
            parts.append(physical[i])
        text = " ".join(parts)
        out.append(LogicalLine(start + 1, text, physical[start].startswith("\t")))
        i += 1
    return out


def make_references(text: str) -> set[str]:
    """Names of make variables ``text`` expands: ``$(NAME)``, ``${NAME}``,
    ``$(NAME:a=b)`` and those nested inside function calls. ``$$`` is an
    escaped dollar, never an expansion."""
    found: set[str] = set()
    i = 0
    while i < len(text):
        if text[i] != "$":
            i += 1
            continue
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if nxt == "$":
            i += 2
            continue
        if nxt in "({":
            match = _NAME.match(text, i + 2)
            if match is not None:
                end = match.end()
                tail = text[end] if end < len(text) else ""
                if tail in ":)}":
                    found.add(match.group(0))
            i += 2
            continue
        i += 1
    found |= set(_VALUE_REF.findall(text))
    found |= set(_PRINTENV_REF.findall(text))
    return found


def _make_printer_arguments(text: str) -> list[str]:
    """The argument text of every ``$(info|warning|error ...)`` call in
    ``text``, read to its balanced closing bracket."""
    args: list[str] = []
    for match in _MAKE_PRINTER.finditer(text):
        opener = text[match.start() + 1]
        closer = ")" if opener == "(" else "}"
        depth, j = 1, match.end()
        while j < len(text) and depth:
            if text[j] == opener:
                depth += 1
            elif text[j] == closer:
                depth -= 1
            j += 1
        args.append(text[match.end() : j - 1 if depth == 0 else j])
    return args


def _strip_comment(text: str) -> str:
    """Drop an unescaped ``#`` comment from a non-recipe line."""
    out = []
    escaped = False
    for ch in text:
        if ch == "#" and not escaped:
            break
        escaped = ch == "\\" and not escaped
        out.append(ch)
    return "".join(out)


def definitions(lines: list[LogicalLine]) -> list[tuple[int, str, str]]:
    """Every ``(lineno, name, value)`` variable assignment outside recipes,
    including target-specific ones (``target: NAME = value``)."""
    found: list[tuple[int, str, str]] = []
    for line in lines:
        if line.recipe:
            continue
        body = _strip_comment(line.text)
        match = _ASSIGNMENT.match(body)
        if match is None:
            head, colon, rest = body.partition(":")
            if not colon or "=" in head:
                continue
            match = _ASSIGNMENT.match(rest)
            if match is None:
                continue
        found.append((line.lineno, match.group("name"), match.group("value").strip()))
    return found


def _indirect_credential_names(defs: list[tuple[int, str, str]]) -> set[str]:
    """Names whose own definition references a credential-named variable —
    the one level of indirection (``PG_DSN_ENV := CCF_TEST_POSTGRES_DSN=$(...)``)
    a suffix rule alone would miss."""
    return {
        name
        for _, name, value in defs
        if any(CREDENTIAL_NAME.search(ref) for ref in make_references(value))
    }


def credential_names(defs: list[tuple[int, str, str]], referenced: set[str]) -> set[str]:
    """The credential variables: by name, plus one level of indirection."""
    by_name = {name for name in referenced if CREDENTIAL_NAME.search(name)}
    by_name |= {name for _, name, _ in defs if CREDENTIAL_NAME.search(name)}
    return by_name | _indirect_credential_names(defs)


def _silenced(recipe_text: str) -> bool:
    """True iff the logical recipe line begins with ``@`` among its prefix
    characters (``@``, ``-``, ``+`` in any order, after the tab)."""
    prefix = re.match(r"^\t[ \t@+\-]*", recipe_text)
    return prefix is not None and "@" in prefix.group(0)


def check_source(source: str, path: str = "Makefile") -> list[str]:
    """Findings for one Makefile's text, as ``path:line rule message``."""
    lines = logical_lines(source)
    defs = definitions(lines)
    referenced: set[str] = set()
    for line in lines:
        referenced |= make_references(line.text)
    creds = credential_names(defs, referenced)

    findings: list[str] = []
    for lineno, name, value in defs:
        if USERINFO.search(value) or TOKEN_USERINFO.search(value):
            findings.append(
                f"{path}:{lineno} {RULE} {name} bakes a credential default"
                " (URL userinfo `://user:secret@`); require the value from the"
                " environment and refuse by name when it is unset"
            )
        elif name.endswith("PASSWORD") and _ANY_REF.sub("", value).strip():
            findings.append(
                f"{path}:{lineno} {RULE} {name} bakes a literal password;"
                " require it from the environment"
            )
    for line in lines:
        for arg in _make_printer_arguments(line.text):
            printed = make_references(arg) & creds
            if printed:
                findings.append(
                    f"{path}:{line.lineno} {RULE} $(info/warning/error) prints"
                    f" {', '.join(sorted(printed))}; make writes it whatever the"
                    " line's prefix"
                )
        if not line.recipe:
            continue
        refs = make_references(line.text) & creds
        if refs and not _silenced(line.text):
            findings.append(
                f"{path}:{line.lineno} {RULE} recipe line expands"
                f" {', '.join(sorted(refs))} and make will echo it; begin the"
                " logical line with `@`"
            )
        if _PRINTER.search(line.text):
            shell_refs = {n for n in _SHELL_REF.findall(line.text) if CREDENTIAL_NAME.search(n)}
            printed = refs | shell_refs
            if printed:
                findings.append(
                    f"{path}:{line.lineno} {RULE} recipe prints"
                    f" {', '.join(sorted(printed))} with echo/printf; `@` does"
                    " not stop the command's own output"
                )
        if _SET_XTRACE.search(line.text):
            findings.append(
                f"{path}:{line.lineno} {RULE} `set -x` in a recipe makes the"
                " shell echo every expanded command, credentials included"
            )
    return findings


def check_tree(base: pathlib.Path) -> list[str]:
    """Whole-tree entry point for ``python -m tools.lints``."""
    findings: list[str] = []
    for relpath in MAKEFILES:
        path = base / relpath
        if path.is_file():
            findings.extend(check_source(path.read_text(encoding="utf-8"), relpath))
    return findings
