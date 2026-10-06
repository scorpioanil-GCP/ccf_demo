"""`ignored-secrets` — key material is ignored by git, and none is tracked (LOW-04).

CLAUDE.md §2.2 says *never a secret in the tree*. The repository's
``.gitignore`` is the mechanism that keeps an operator's key file out of a
``git add -A``; this rule holds that file to the set of key-material patterns
the row ruled (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
LOW-04 and its MEASURED block, ``D-IMPL-372``): the JWK files
``FileBackedKeySource`` reads (``src/ccf/peering/identity.py::FileBackedKeySource``),
the token file ``FileTokenSource`` reads
(``runtime/ccf_runtime/mcp/auth.py::FileTokenSource``), PEM, PKCS#12 and Java
keystores, and ``.env`` with its per-environment variants.

Three refusals:

1. **Missing pattern.** Each of ``REQUIRED_PATTERNS`` must appear in
   ``.gitignore`` as an active line spelled exactly so. A commented-out line
   does not count, and neither does a negation.
2. **Re-opening negation.** A ``!`` line whose last path segment would match
   a key-material file name re-includes what a required pattern excluded
   (``!keys/*.jwk``), so it is refused.
3. **Tracked key material.** ``git ls-files`` lists the tracked set; a tracked
   path whose file name matches a required pattern is refused — ignoring a file
   does not untrack one already committed.

The third half needs git. When ``git`` is not installed, or the base is not the
top of a git checkout, the rule cannot list tracked files; it then still checks
the patterns and reports a finding that says the tracked-file half did not run.
That is fail-closed by design: *don't know* is not reported as *pass*
(CLAUDE.md §3.1).

The patterns are mechanism, not a deployment value — they name file shapes, not
any deployment's files. Exit code is the gate signal, as for every rule in
``tools/lints/__main__.py``; there is no allowlist (D-13).
"""

from __future__ import annotations

import fnmatch
import pathlib
import shutil
import subprocess
from collections.abc import Iterable

RULE = "ignored-secrets"

#: The ignore file the rule reads, relative to the base.
GITIGNORE = ".gitignore"

#: Every pattern the row ruled, spelled as the ``.gitignore`` line must be.
REQUIRED_PATTERNS: tuple[str, ...] = (
    "*.pem",
    "*.jwk",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*.keystore",
    "tokens.json",
    ".env",
    ".env.*",
)

#: One representative file name per required pattern; a negation whose last
#: segment matches any of them re-opens that pattern.
_SAMPLES: tuple[str, ...] = (
    "x.pem",
    "x.jwk",
    "x.key",
    "x.p12",
    "x.pfx",
    "x.jks",
    "x.keystore",
    "tokens.json",
    ".env",
    ".env.x",
)


def _finding(relpath: str, lineno: int, message: str) -> str:
    return f"{relpath}:{lineno} {RULE} {message}"


def check_patterns(text: str, relpath: str = GITIGNORE) -> list[str]:
    """Refusals 1 and 2 over the text of one ``.gitignore``."""
    active: set[str] = set()
    findings: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            segment = line[1:].rstrip("/").rsplit("/", 1)[-1]
            if any(fnmatch.fnmatchcase(sample, segment) for sample in _SAMPLES):
                findings.append(
                    _finding(relpath, lineno, f"negation {line!r} re-includes key material")
                )
            continue
        active.add(line)
    for pattern in REQUIRED_PATTERNS:
        if pattern not in active:
            findings.append(
                _finding(relpath, 1, f"key-material pattern {pattern!r} is not ignored")
            )
    return findings


def _is_key_material(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in REQUIRED_PATTERNS)


def check_tracked(paths: Iterable[str]) -> list[str]:
    """Refusal 3 over a list of tracked paths (``git ls-files`` output)."""
    return [
        _finding(path, 1, "tracked file is key material; untrack it and rotate the secret")
        for path in paths
        if _is_key_material(path)
    ]


def _tracked_paths(base: pathlib.Path) -> list[str] | None:
    """The tracked set when ``base`` is the top of a git checkout, else ``None``."""
    if shutil.which("git") is None:
        return None
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=base,
        capture_output=True,
        text=True,
        check=False,
    )
    if top.returncode != 0 or pathlib.Path(top.stdout.strip()).resolve() != base.resolve():
        return None
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=base, capture_output=True, check=False
    )
    if listed.returncode != 0:
        return None
    return [p for p in listed.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def check_tree(base: pathlib.Path) -> list[str]:
    """Whole-tree entry point for ``python -m tools.lints``."""
    path = base / GITIGNORE
    if not path.is_file():
        # A base that is not a project (no ``pyproject.toml``) has nothing to
        # guard — the runner's "missing trees are skipped" contract, as
        # ``tools/lints/dependency_lock.py::check_tree`` reads it. A project
        # with no ignore file ignores nothing, and that is refused.
        if not (base / "pyproject.toml").is_file():
            return []
        return [_finding(GITIGNORE, 1, "no .gitignore: key material is not ignored")]
    findings = check_patterns(path.read_text(encoding="utf-8"), GITIGNORE)
    tracked = _tracked_paths(base)
    if tracked is None:
        findings.append(
            _finding(
                GITIGNORE,
                1,
                "not a git checkout (or git is not installed): the tracked-file"
                " half did not run; patterns were checked alone",
            )
        )
    else:
        findings.extend(check_tracked(tracked))
    return findings
