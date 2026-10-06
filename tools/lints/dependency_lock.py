"""`dependency-lock` — CI installs only hash-verified, locked dependencies (SEC-028).

An unhashed ``pip install -e ".[dev]"`` resolves every transitive dependency
from the index at run time, so a compromised or yanked-and-replaced release
reaches the build that produces the SDK a bank installs. Build isolation does
the same for the *build* set: pip fetches ``setuptools`` and
``setuptools_scm`` unhashed into a temporary environment before it builds the
project. ``D-IMPL-369`` ruled that the lock carries the build dependencies too.

The refusals, over the repository's ``requirements.lock``, every
``.github/workflows/*.yml`` / ``*.yaml`` and the ``Makefile``:

1. **The lock exists** at ``requirements.lock``.
2. **Every requirement in it is hashed.** Each logical entry (backslash
   continuations joined) carries ``--hash=sha256:<64 hex>``; an entry without
   one, or a direct reference (``name @ file://...``, ``-e``), is refused —
   ``pip install --require-hashes`` would refuse it at install time anyway, and
   the lint says so before CI does.
3. **The build set is in it**: ``setuptools==`` and ``setuptools-scm==``, and
   the lock tool itself, ``pip-tools==`` (ruling Q17 adds it to the ``dev``
   extra so the lock carries it).
4. **Every install of dependencies reads the lock**: every ``pip install`` that
   is not an editable project install is exactly
   ``pip install --require-hashes -r requirements.lock``.
5. **Every editable project install fetches nothing**: exactly
   ``pip install -e <path> --no-deps --no-build-isolation``. ``--no-deps``
   stops a resolve against the index; ``--no-build-isolation`` stops the
   unhashed build-dependency fetch (measured: without it pip logs
   *"Installing build dependencies"*).

A workflow ``run:`` block and a ``Makefile`` recipe are split into commands
before matching — newlines, backslash continuations, ``&&``, ``||``, ``;``,
``|`` and ``&`` — so a multi-line ``run: |`` cannot hide a second install
behind a first. A pip invocation is ``pip``, ``pip3``, ``pip3.N`` (any path),
``python[3[.N]] [-opts] -m pip`` or ``uv pip``, with any global options
(``-q``, ``--no-cache-dir``, ``--log FILE``, ...) between the program and
``install``; leading ``NAME=value`` assignments are skipped. Every OTHER
installer — ``uv sync``/``add``/``run``/``tool``, ``uvx``, ``uv pip sync``,
``poetry``, ``pdm``, ``pipenv``, ``pipx``, ``conda``/``mamba``,
``easy_install``, ``pip-sync``, ``setup.py install`` — is refused by name as an
unhashed install path (``tools/lints/dependency_lock.py::OTHER_INSTALLERS``).
An editable operand must be in-tree: ``.``, ``./...`` or a relative path with
no scheme, VCS prefix, absolute root or ``..`` escape (SEC-028 corrective
round).

The rule applies to a base that is a project — one that has a
``pyproject.toml`` or a ``.github/workflows`` directory — so the runner's
synthetic trees stay clean. The rule is mechanism, not a deployment value: the
row ruled it (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
SEC-028, ``D-IMPL-368``, ``D-IMPL-369``). Exit code is the gate signal, as for
every rule in ``tools/lints/__main__.py``; there is no allowlist (D-13).
"""

from __future__ import annotations

import pathlib
import re
import shlex
from typing import Any, Iterator

import yaml

from tools.lints import ci_posture

RULE = "dependency-lock"

#: The lock, relative to the base.
LOCK = "requirements.lock"

#: The entries the lock must carry: the build set (D-IMPL-369) and the lock
#: tool (Q17).
REQUIRED_PINS: tuple[str, ...] = ("setuptools", "setuptools-scm", "pip-tools")

_HASH = re.compile(r"--hash=sha256:([0-9a-f]+)")
_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._\-]*)(\[[^\]]*\])?==\S+")
_SPLIT = re.compile(r"\s*(?:&&|\|\||;|\|&?|(?<![<>&])&(?![>&]))\s*")

#: The one accepted form of a dependency install, as a set of argument words.
LOCKED_INSTALL = frozenset({"--require-hashes", "-r", LOCK})


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _lock_entries(text: str) -> Iterator[tuple[int, str]]:
    """``(lineno, entry)`` per logical lock entry, comments and blanks dropped."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        start = i
        parts = [lines[i]]
        while parts[-1].rstrip().endswith("\\") and i + 1 < len(lines):
            parts[-1] = parts[-1].rstrip()[:-1]
            i += 1
            parts.append(lines[i])
        i += 1
        entry = " ".join(p.split(" #", 1)[0] if not p.lstrip().startswith("#") else "" for p in parts)
        entry = entry.strip()
        if entry and not entry.startswith("#"):
            yield start + 1, entry


def check_lock(text: str, path: str = LOCK) -> list[str]:
    """Findings for the lock's text."""
    findings: list[str] = []
    pinned: set[str] = set()
    for lineno, entry in _lock_entries(text):
        if entry.startswith("--") and not entry.startswith("--hash"):
            continue  # a pip option line (`--index-url`, ...), not a requirement
        hashes = _HASH.findall(entry)
        pin = _PIN.match(entry)
        if pin is None:
            findings.append(
                f"{path}:{lineno} {RULE} `{entry[:80]}` is not a `name==version`"
                " pin; a direct reference or an editable entry cannot be hashed"
            )
            continue
        if not hashes or any(len(h) != 64 for h in hashes):
            findings.append(
                f"{path}:{lineno} {RULE} `{pin.group(0)}` carries no"
                " `--hash=sha256:` (64 hex); regenerate with `--generate-hashes`"
            )
        pinned.add(_norm(pin.group(1)))
    for name in REQUIRED_PINS:
        if _norm(name) not in pinned:
            findings.append(
                f"{path}:1 {RULE} the lock carries no `{name}==` entry; the"
                " build set and the lock tool are locked too (D-IMPL-369, Q17)"
            )
    return findings


def commands(script: str) -> list[str]:
    """Split a shell script into single commands: continuations joined, then
    newlines, ``&&``, ``||`` and ``;`` as separators. Comment lines dropped."""
    joined = re.sub(r"\\\n", " ", script)
    out: list[str] = []
    for line in joined.splitlines():
        if line.strip().startswith("#"):
            continue
        out.extend(c.strip() for c in _SPLIT.split(line) if c.strip())
    return out


#: ``pip``, ``pip3``, ``pip3.12`` — any pip console script, by basename.
_PIP_PROGRAM = re.compile(r"^pip(?:\d+(?:\.\d+)*)?$")
#: ``python``, ``python3``, ``python3.12`` — an interpreter that may run ``-m pip``.
_PYTHON_PROGRAM = re.compile(r"^python(?:\d+(?:\.\d+)*)?$")
#: A leading ``NAME=value`` environment assignment before the program.
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
#: pip and uv global options that consume the NEXT word as their value, so the
#: subcommand search does not mistake that value for the subcommand.
_VALUED_GLOBAL_OPTIONS = frozenset({
    "--log", "--log-file", "--proxy", "--retries", "--timeout", "--exists-action",
    "--trusted-host", "--cert", "--client-cert", "--cache-dir", "--python",
    "--keyring-provider", "--use-feature", "--use-deprecated", "--directory",
    "--project", "--config-file", "--color",
})
#: Dependency installers that are not the ruled pip form, by program, and the
#: subcommands of each that install (``None``: every invocation installs).
#: Each is an unhashed install path: none of them reads ``requirements.lock``
#: with ``--require-hashes``.
OTHER_INSTALLERS: dict[str, frozenset[str] | None] = {
    "uv": frozenset({"sync", "add", "run", "tool"}),
    "uvx": None,
    "poetry": frozenset({"install", "add", "update", "sync"}),
    "pdm": frozenset({"install", "add", "update", "sync"}),
    "pipenv": frozenset({"install", "sync", "update"}),
    "pipx": None,
    "conda": frozenset({"install", "create", "update", "env"}),
    "mamba": frozenset({"install", "create", "update", "env"}),
    "micromamba": frozenset({"install", "create", "update", "env"}),
    "easy_install": None,
    "pip-sync": None,
}


def _words(command: str) -> list[str]:
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    while words and _ENV_ASSIGNMENT.match(words[0]):
        words = words[1:]
    return words


def _subcommand(words: list[str], start: int) -> int | None:
    """Index of the first non-option word at or after ``start``, skipping
    global options (``-q``, ``--no-cache-dir``, ``--log FILE``, ...)."""
    i = start
    while i < len(words):
        word = words[i]
        if not word.startswith("-"):
            return i
        i += 2 if word in _VALUED_GLOBAL_OPTIONS else 1
    return None


def _pip_entry(words: list[str]) -> int | None:
    """Index just past the pip program if ``words`` invokes pip: ``pip``,
    ``pip3.N``, ``python -m pip``, ``python3 -I -m pip``, ``uv pip``."""
    if not words:
        return None
    program = pathlib.PurePosixPath(words[0]).name
    if _PIP_PROGRAM.match(program):
        return 1
    if _PYTHON_PROGRAM.match(program):
        for i in range(1, len(words)):
            if words[i] == "-m" and i + 1 < len(words):
                return i + 2 if words[i + 1] == "pip" else None
            if words[i] == "-mpip":
                return i + 1
            if not words[i].startswith("-"):
                return None
        return None
    if program == "uv":
        sub = _subcommand(words, 1)
        if sub is not None and words[sub] == "pip":
            return sub + 1
    return None


def _pip_install_args(command: str) -> list[str] | None:
    """The words after ``install`` if ``command`` is a pip install, in any of
    the spellings ``_pip_entry`` recognizes, global options tolerated between
    the program and ``install``."""
    words = _words(command)
    entry = _pip_entry(words)
    if entry is None:
        return None
    sub = _subcommand(words, entry)
    if sub is None or words[sub] != "install":
        return None
    return words[sub + 1 :]


def _other_installer(command: str) -> str | None:
    """The name of a non-pip installer invocation, or None."""
    words = _words(command)
    if not words:
        return None
    program = pathlib.PurePosixPath(words[0]).name
    if program not in OTHER_INSTALLERS:
        if _PYTHON_PROGRAM.match(program) and len(words) > 2 and words[1].endswith("setup.py"):
            if words[2] in {"install", "develop"}:
                return f"setup.py {words[2]}"
        return None
    subs = OTHER_INSTALLERS[program]
    if subs is None:
        return program
    sub = _subcommand(words, 1)
    if program == "uv" and sub is not None and words[sub] == "pip":
        second = _subcommand(words, sub + 1)
        if second is not None and words[second] == "sync":
            return "uv pip sync"
        return None
    if sub is not None and words[sub] in subs:
        return f"{program} {words[sub]}"
    return None


def _in_tree(operand: str) -> bool:
    """An editable operand is in-tree: ``.``, ``./...`` or a relative path with
    no scheme, no VCS prefix, no absolute root and no ``..`` escape."""
    if "://" in operand or re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*:", operand):
        return False
    path = pathlib.PurePosixPath(operand)
    return not path.is_absolute() and ".." not in path.parts


def check_command(command: str, where: str) -> list[str]:
    """Findings for one shell command."""
    other = _other_installer(command)
    if other is not None:
        return [
            f"{where} {RULE} `{command}` uses `{other}`, an unhashed install"
            f" path; the only dependency install is `pip install --require-hashes"
            f" -r {LOCK}`"
        ]
    args = _pip_install_args(command)
    if args is None:
        return []
    if "-e" in args or "--editable" in args or any(a.startswith("--editable=") for a in args):
        flags = {a for a in args if a.startswith("-")}
        operands = [a for a in args if not a.startswith("-")]
        operands += [a.split("=", 1)[1] for a in args if a.startswith("--editable=")]
        flags = {f.split("=", 1)[0] for f in flags}
        problems = []
        if "--no-deps" not in flags:
            problems.append("`--no-deps`")
        if "--no-build-isolation" not in flags:
            problems.append("`--no-build-isolation`")
        extra = flags - {"-e", "--editable", "--no-deps", "--no-build-isolation"}
        bad_operand = len(operands) != 1 or "[" in operands[0] or not _in_tree(operands[0])
        if problems or extra or bad_operand:
            return [
                f"{where} {RULE} `{command}` must be exactly `pip install -e <path>"
                " --no-deps --no-build-isolation` with an in-tree path"
                + (f" (missing {', '.join(problems)})" if problems else "")
                + (f" (unexpected {', '.join(sorted(extra))})" if extra else "")
                + (f" (operand {operands!r} is not one in-tree path)" if bad_operand else "")
            ]
        return []
    if set(args) != LOCKED_INSTALL or len(args) != len(LOCKED_INSTALL):
        return [
            f"{where} {RULE} `{command}` installs dependencies outside the lock;"
            f" the only dependency install is `pip install --require-hashes -r {LOCK}`"
        ]
    return []


def _run_blocks(doc: dict[Any, Any]) -> Iterator[tuple[str, str]]:
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return
    for job_id, job in jobs.items():
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            continue
        for index, step in enumerate(job["steps"]):
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                yield f"jobs.{job_id}.steps[{index}]", step["run"]


def check_workflow(text: str, path: str) -> list[str]:
    """Findings for one workflow's text."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"{path}:1 {RULE} workflow does not parse as YAML: {exc}"]
    if not isinstance(doc, dict):
        return [f"{path}:1 {RULE} workflow is not a mapping"]
    findings: list[str] = []
    for where, script in _run_blocks(doc):
        for command in commands(script):
            findings.extend(check_command(command, f"{path}:1 {where}"))
    return findings


def check_makefile(text: str, path: str = "Makefile") -> list[str]:
    """Findings for the Makefile's recipe lines (tab-prefixed, joined)."""
    findings: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        start = i
        if not lines[i].startswith("\t"):
            i += 1
            continue
        parts = [lines[i]]
        while parts[-1].endswith("\\") and i + 1 < len(lines):
            parts[-1] = parts[-1][:-1]
            i += 1
            parts.append(lines[i])
        i += 1
        recipe = " ".join(parts).lstrip("\t").lstrip("@-+ ")
        for command in commands(recipe):
            findings.extend(check_command(command, f"{path}:{start + 1}"))
    return findings


def check_tree(base: pathlib.Path) -> list[str]:
    """Whole-tree entry point for ``python -m tools.lints``."""
    workflows = ci_posture.workflow_paths(base)
    if not workflows and not (base / "pyproject.toml").is_file():
        return []
    findings: list[str] = []
    lock = base / LOCK
    if not lock.is_file():
        findings.append(
            f"{LOCK}:1 {RULE} no `{LOCK}`; generate it with pip-compile"
            " --generate-hashes --all-build-deps (README.md)"
        )
    else:
        findings.extend(check_lock(lock.read_text(encoding="utf-8")))
    for path in workflows:
        rel = path.relative_to(base).as_posix()
        findings.extend(check_workflow(path.read_text(encoding="utf-8"), rel))
    makefile = base / "Makefile"
    if makefile.is_file():
        findings.extend(check_makefile(makefile.read_text(encoding="utf-8")))
    return findings
