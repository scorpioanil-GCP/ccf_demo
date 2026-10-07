"""`dependency-lock-freshness` — the lock agrees with the declaration (SEC-028-F1).

``dependency-lock`` (``tools/lints/dependency_lock.py::check_tree``, SEC-028)
proves CI installs only the hashed ``requirements.lock``. It cannot see that
the lock has drifted from what ``pyproject.toml`` declares: a pin bump in
``pyproject.toml`` with no regeneration leaves CI installing the *old* lock,
green, and the declared requirement is a statement nothing enforces. The row
(``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
SEC-028-F1, authorized by ``D-IMPL-370``) closes that gap.

The refusals, over the repository's ``pyproject.toml`` and
``requirements.lock``:

1. **The lock records how it was compiled.** Its pip-compile header names
   exactly the ruled extras, ``LOCKED_EXTRAS`` (the ``D-IMPL-369``
   invocation in ``README.md`` "Regenerating the lock"), and carries
   ``--all-build-deps``. A lock compiled without an extra silently drops its
   requirements; a lock compiled with ``chroma`` pulls ``chromadb`` into every
   CI job. Each ruled extra must also exist in
   ``[project.optional-dependencies]``.
2. **Every declared requirement is in the lock and its pin satisfies the
   declared specifier.** The declared set is ``[project].dependencies``, every
   ruled extra followed through the project's own self-references
   (``dev`` -> ``ccf-sdk[harnesses]`` -> ``ccf-sdk[adk,claude-agent,langgraph]``), and
   ``[build-system].requires`` (``D-IMPL-369``: the lock carries the build
   set). A requirement whose environment marker is false for the interpreter
   running the lint is skipped, as pip-compile would skip it. A declared
   requirement's extras must be among the locked entry's extras
   (``--no-strip-extras``).

Extras the lock is deliberately **not** compiled with (``chroma``, ...) are out
of scope: nothing installs them from the lock.

The rule applies to a base that is a project — one that has a
``pyproject.toml`` or a ``.github/workflows`` directory — as ``dependency-lock``
does, so the runner's synthetic trees stay clean. It is mechanism, not a
deployment value (CLAUDE.md §11, "Mechanism, not values"): ``LOCKED_EXTRAS``
is the repository's own ruled lock invocation, not a choice the SDK makes for a
deployment. Exit code is the gate signal, as for every rule in
``tools/lints/__main__.py``; there is no allowlist (D-13).
"""

from __future__ import annotations

import pathlib
import shlex
import tomllib
from dataclasses import dataclass
from typing import Any

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from tools.lints import ci_posture
from tools.lints.dependency_lock import LOCK, _PIN, _lock_entries, _norm

RULE = "dependency-lock-freshness"

PYPROJECT = "pyproject.toml"

#: The extras the lock is compiled with — the ruled invocation (D-IMPL-369,
#: README.md "Regenerating the lock"). Changing this set is a ruling, made here.
LOCKED_EXTRAS: frozenset[str] = frozenset({"dev", "neo4j", "mongo"})

#: The header flag that puts the build set in the lock (D-IMPL-369).
ALL_BUILD_DEPS = "--all-build-deps"


@dataclass(frozen=True)
class Pin:
    """One locked entry: ``name[extras]==version``."""

    version: str
    extras: frozenset[str]


def lock_pins(text: str) -> dict[str, Pin]:
    """``normalized name -> Pin`` for every ``name==version`` entry in the lock."""
    pins: dict[str, Pin] = {}
    for _, entry in _lock_entries(text):
        match = _PIN.match(entry)
        if match is None:
            continue  # an option line or an unpinnable entry: `dependency-lock`'s finding
        extras = match.group(2) or ""
        version = match.group(0).split("==", 1)[1]
        pins[_norm(match.group(1))] = Pin(
            version=version,
            extras=frozenset(_norm(e) for e in extras.strip("[]").split(",") if e.strip()),
        )
    return pins


def lock_header(text: str) -> list[str] | None:
    """The pip-compile command words recorded in the lock's header, or None."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            break  # the header is the leading comment block
        body = stripped.lstrip("#").strip()
        if body.startswith("pip-compile "):
            try:
                return shlex.split(body)
            except ValueError:
                return body.split()
    return None


def header_extras(words: list[str]) -> set[str]:
    """The ``--extra`` values named by the header's command words."""
    extras: set[str] = set()
    for i, word in enumerate(words):
        if word.startswith("--extra="):
            extras.add(word.split("=", 1)[1])
        elif word == "--extra" and i + 1 < len(words):
            extras.add(words[i + 1])
    return extras


def _line_of(text: str, needle: str) -> int:
    for lineno, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return lineno
    return 1


def _table(doc: dict[str, Any], key: str) -> dict[str, Any]:
    value = doc.get(key)
    return value if isinstance(value, dict) else {}


def declared(
    doc: dict[str, Any], text: str
) -> tuple[list[tuple[str, str, Requirement, str | None]], list[str]]:
    """The declared requirement set and the findings met assembling it.

    Each item is ``(label, raw, requirement, extra)`` — ``extra`` is the extra
    the requirement was declared under (marker evaluation), else None.
    """
    findings: list[str] = []
    out: list[tuple[str, str, Requirement, str | None]] = []
    project = _table(doc, "project")
    own = _norm(str(project.get("name", "")))
    optional = project.get("optional-dependencies")
    optional = optional if isinstance(optional, dict) else {}

    def parse(label: str, raws: Any, extra: str | None) -> list[Requirement]:
        reqs: list[Requirement] = []
        if not isinstance(raws, list):
            findings.append(f"{PYPROJECT}:1 {RULE} `{label}` is not a list of requirements")
            return reqs
        for raw in raws:
            try:
                req = Requirement(str(raw))
            except InvalidRequirement as exc:
                findings.append(
                    f"{PYPROJECT}:{_line_of(text, str(raw))} {RULE} `{raw}` in `{label}`"
                    f" is not a valid requirement: {exc}"
                )
                continue
            reqs.append(req)
            if not (own and _norm(req.name) == own):
                out.append((label, str(raw), req, extra))
        return reqs

    parse("[project].dependencies", project.get("dependencies", []), None)

    pending = sorted(LOCKED_EXTRAS)
    seen: set[str] = set()
    while pending:
        extra = pending.pop(0)
        if extra in seen:
            continue
        seen.add(extra)
        if extra not in optional:
            if extra in LOCKED_EXTRAS:
                findings.append(
                    f"{PYPROJECT}:1 {RULE} the lock is compiled with extra `{extra}`"
                    " but `[project.optional-dependencies]` declares no such extra"
                )
            else:
                findings.append(
                    f"{PYPROJECT}:1 {RULE} a self-reference names extra `{extra}`,"
                    " which `[project.optional-dependencies]` does not declare"
                )
            continue
        label = f"[project.optional-dependencies].{extra}"
        for req in parse(label, optional[extra], extra):
            if own and _norm(req.name) == own:
                pending.extend(sorted(req.extras))

    build = _table(doc, "build-system")
    parse("[build-system].requires", build.get("requires", []), None)
    return out, findings


def check(pyproject_text: str, lock_text: str) -> list[str]:
    """Findings for one declaration and one lock."""
    findings: list[str] = []
    words = lock_header(lock_text)
    if words is None:
        findings.append(
            f"{LOCK}:1 {RULE} the lock carries no pip-compile header recording its"
            " extras; regenerate it with the command in README.md"
        )
    else:
        named = header_extras(words)
        for extra in sorted(LOCKED_EXTRAS - named):
            findings.append(
                f"{LOCK}:1 {RULE} the lock's compile header does not name `--extra={extra}`;"
                " its requirements are not in the lock"
            )
        for extra in sorted(named - LOCKED_EXTRAS):
            findings.append(
                f"{LOCK}:1 {RULE} the lock's compile header names `--extra={extra}`,"
                f" outside the ruled set {sorted(LOCKED_EXTRAS)}"
            )
        if ALL_BUILD_DEPS not in words:
            findings.append(
                f"{LOCK}:1 {RULE} the lock's compile header has no `{ALL_BUILD_DEPS}`;"
                " the build set is locked too (D-IMPL-369)"
            )

    try:
        doc = tomllib.loads(pyproject_text)
    except tomllib.TOMLDecodeError as exc:
        return findings + [f"{PYPROJECT}:1 {RULE} does not parse as TOML: {exc}"]

    requirements, assembly = declared(doc, pyproject_text)
    findings.extend(assembly)
    pins = lock_pins(lock_text)
    environment = {k: str(v) for k, v in default_environment().items()}
    for label, raw, req, under in requirements:
        if req.marker is not None and not req.marker.evaluate(
            {**environment, "extra": under if under is not None else ""}
        ):
            continue
        where = f"{PYPROJECT}:{_line_of(pyproject_text, raw)} {RULE}"
        pin = pins.get(_norm(req.name))
        if pin is None:
            findings.append(
                f"{where} `{raw}` (`{label}`) is declared but `{LOCK}` carries no"
                f" `{req.name}==` entry; regenerate the lock (README.md)"
            )
            continue
        try:
            satisfied = req.specifier.contains(Version(pin.version), prereleases=True)
        except InvalidVersion:
            satisfied = False
        if not satisfied:
            findings.append(
                f"{where} `{raw}` (`{label}`) is not satisfied by the locked"
                f" `{req.name}=={pin.version}`; regenerate the lock (README.md)"
            )
        missing = {_norm(e) for e in req.extras} - pin.extras
        if missing:
            findings.append(
                f"{where} `{raw}` (`{label}`) requests extras {sorted(missing)} the"
                f" locked `{req.name}` entry does not carry; regenerate the lock"
            )
    return findings


def check_tree(base: pathlib.Path) -> list[str]:
    """Whole-tree entry point for ``python -m tools.lints``."""
    pyproject = base / PYPROJECT
    if not ci_posture.workflow_paths(base) and not pyproject.is_file():
        return []
    findings: list[str] = []
    lock = base / LOCK
    if not pyproject.is_file():
        findings.append(f"{PYPROJECT}:1 {RULE} no `{PYPROJECT}`; nothing declares what the lock must hold")
    if not lock.is_file():
        findings.append(f"{LOCK}:1 {RULE} no `{LOCK}` to compare with the declaration")
    if findings:
        return findings
    return check(pyproject.read_text(encoding="utf-8"), lock.read_text(encoding="utf-8"))
