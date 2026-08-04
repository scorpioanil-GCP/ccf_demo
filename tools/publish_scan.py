"""D-02 — the never-publish gate (CLAUDE.md §2.2; rulings D-02 and D-20).

The whitepaper is proprietary IP and the phase deliverables under `.planning/`
and `docs/` are internal. Neither may ever reach the published documentation
tree. This module is the mechanism of record for that guarantee, and it is
built to read as a fourth CCF invariant lint rather than as a novel script:
same finding format, same blocking posture, same tuning-knobs-as-documented-
constants discipline as `tools/lints/`.

Four rules:

``pub01-whitepaper-shingle``
    A run of `SHINGLE_WORDS` consecutive normalized words from the whitepaper
    body appears in a published file. Normalization strips HTML tags and
    backtick code spans first, so neither element boundaries nor inline markup
    can mask a quote.

``pub02-internal-path``
    A published path names an internal deliverable (`INTERNAL_PATH_TOKENS`),
    or a published page cites a whitepaper figure by its `Fig-CHNN-NN` name.
    Token matching is boundary-anchored the way `matches_module` is
    dot-bounded — a lookalike filename must not match, and a real one must not
    be missed.

``pub03-symlink``
    A symlink exists under the pre-build source tree. mkdocs copies file
    *content*, so `public/x.md -> ../docs/CCF_Whitepaper_1-2.md` publishes the
    whitepaper outright.

``pub04-include-escape``
    A snippet-include directive in public Markdown names a target outside
    `INCLUDE_ALLOWED_PREFIXES`. `restrict_base_path` blocks `../` traversal
    above the base path but not sibling access, so this is checked here — and
    it is checked as a positive allowlist over a *normalized* target, in both
    the inline and the block directive forms, because a denylist of internal
    prefixes is defeated by `./docs/x`, by `public/../docs/x`, and by any
    internal tree nobody remembered to enumerate.

Unlike CINV-01 — which has legitimate exceptions and therefore takes
`tools/lints/allowlist.yaml` — this scan takes **no allowlist**, and it has no
report-only, warn-only or `--exit-zero` mode. That is D-20, and it is
deliberate: the thirteen docstrings that were leaking whitepaper prose when
this gate was written were *reworked*, not excepted, because a maintained
exception list is precisely what D-02 was chosen over. Exit code is the only
gate signal.

Usage::

    python tools/publish_scan.py site
    python tools/publish_scan.py --pre-build
"""

from __future__ import annotations

import argparse
import functools
import pathlib
import posixpath
import re
import sys
from typing import Sequence

from tools.lints import format_finding

RULE_SHINGLE = "pub01-whitepaper-shingle"
RULE_INTERNAL_PATH = "pub02-internal-path"
RULE_SYMLINK = "pub03-symlink"
RULE_INCLUDE_ESCAPE = "pub04-include-escape"

# --- tuning knobs ----------------------------------------------------------

#: Window length for the shingle intersection, measured against this repo
#: (14-RESEARCH.md, 2026-08-03). N=8 flags 22 docstrings and 146
#: positive-control hits in `docs/DESIGN.md` and is noisy; N=10 flags 13 and
#: 60; N=20 flags 2 and the positive control stops firing entirely, which
#: makes the gate useless. Ten is the shortest window with a strong control.
SHINGLE_WORDS = 10

#: The shingle source. Read by this scanner and by nothing else.
WHITEPAPER = "docs/CCF_Whitepaper_1-2.md"

#: The built tree the post-build scan walks — whatever survives to here ships.
SCANNED_TREE = "site"

#: The hand-authored tree the structural guards walk, before mkdocs copies it.
PREBUILD_TREE = "public"

#: Path segments that name an internal deliverable. Matched at word
#: boundaries, never as a bare substring, so `PHASE_INTEGRATION` does not
#: match `PHASE_I` while `PHASE_I1_GATE.md` still does.
INTERNAL_PATH_TOKENS: tuple[str, ...] = (
    "CCF_Whitepaper",
    "SPEC_INVENTORY",
    "PHASE_I",
    "09-ruling-batch-minicycle",
    ".planning",
)

#: The include roots a published page may reach into — a POSITIVE allowlist,
#: because the charter is default-deny and a denylist of internal prefixes is
#: evaded by `./docs/…`, by `public/../docs/…`, and by anything not yet
#: enumerated (`references/`, absolute paths). A target is permitted only if it
#: normalizes to a relative path under one of these roots.
INCLUDE_ALLOWED_PREFIXES: tuple[str, ...] = (
    "examples/",
    "public/",
    "perf/baselines/",
)

#: Individual repo-root files the published tree legitimately embeds. Kept
#: separate from the prefixes so a root-level file cannot open a whole tree.
INCLUDE_ALLOWED_FILES: frozenset[str] = frozenset({"openapi.json"})

#: Directories never worth walking, mirroring the lints runner.
SKIP_DIRS: frozenset[str] = frozenset(
    {"__pycache__", ".git", ".venv", "venv", "build", "dist", ".mypy_cache"}
)

#: Suffixes whose bytes are read as text and scanned for quoted prose. Files
#: outside this set are still path-checked.
TEXT_SUFFIXES: frozenset[str] = frozenset(
    {".html", ".htm", ".md", ".txt", ".json", ".xml", ".js", ".css", ".yml", ".yaml"}
)

_TAG_RE = re.compile(r"<[^>]*>")
_CODE_SPAN_RE = re.compile(r"`[^`]*`")
_NON_WORD_RE = re.compile(r"[^a-z0-9 ]")
_FIGURE_RE = re.compile(r"Fig-CH\d{2}-\d{2}")
#: A whole line that is nothing but a snippet directive. Matching the whole
#: line — rather than searching anywhere in it — is what lets a bare `--8<--`
#: be recognized as the block-form delimiter rather than as a target.
_INCLUDE_LINE_RE = re.compile(r"^\s*-{2,}8<-{2,}\s*\"?([^\"\s]*)\"?\s*$")

#: An inline directive with a target, anywhere on a line. The quotes are
#: required because they are required by `pymdownx.snippets` itself for this
#: form — without them, the code span in the charter's own prose sentence
#: ("No `--8<--` snippet include") reads as a directive whose target is a
#: backtick.
_INCLUDE_INLINE_RE = re.compile(r"-{2,}8<-{2,}\s*\"([^\"]+)\"")


def normalize(text: str) -> list[str]:
    """Lowercased word sequence with markup and code spans removed.

    HTML tags go first so an element boundary inside a quoted sentence cannot
    split a shingle; backtick code spans go next so a rendered identifier does
    not glue two unrelated words together.
    """
    stripped = _CODE_SPAN_RE.sub(" ", _TAG_RE.sub(" ", text))
    return _NON_WORD_RE.sub(" ", stripped.lower()).split()


def shingles_of(words: Sequence[str]) -> set[str]:
    """Every `SHINGLE_WORDS`-long window over `words`."""
    n = SHINGLE_WORDS
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


@functools.lru_cache(maxsize=1)
def whitepaper_shingles() -> frozenset[str]:
    """The whitepaper's shingle set, built once per process.

    Measured at 107,712 shingles in 0.04 s, so no caching layer beyond this
    single memo is warranted.
    """
    text = pathlib.Path(WHITEPAPER).read_text(encoding="utf-8")
    return frozenset(shingles_of(normalize(text)))


def _token_matches(segment: str, token: str) -> bool:
    """Whether `segment` names `token` at word boundaries.

    Anchored the way `tools.lints.matches_module` is dot-bounded: the token
    must not be preceded by an alphanumeric character, and must not be
    followed by a letter. `PHASE_I1_GATE.md` matches `PHASE_I`;
    `PHASE_INTEGRATION` does not.
    """
    pattern = f"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z])"
    return re.search(pattern, segment) is not None


def include_targets(text: str) -> list[tuple[int, str]]:
    """`(lineno, target)` for every snippet include in `text`.

    `pymdownx.snippets` accepts two forms and the gate must see both: the
    inline `--8<-- "target"`, and the block form, in which a bare `--8<--`
    opens a list of one-per-line targets and a second bare `--8<--` closes it.
    A gate that parses only the inline form is defeated by a two-line edit.
    """
    found: list[tuple[int, str]] = []
    in_block = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        whole = _INCLUDE_LINE_RE.match(line)
        if whole is not None and not whole.group(1):
            in_block = not in_block
            continue
        if whole is not None:
            found.append((lineno, whole.group(1)))
            continue
        if in_block:
            stripped = line.strip().strip('"')
            if stripped:
                found.append((lineno, stripped))
            continue
        for target in _INCLUDE_INLINE_RE.findall(line):
            found.append((lineno, target))
    return found


def include_escapes(target: str) -> bool:
    """Whether `target` leaves the permitted include roots.

    Normalization happens before the comparison, so `./docs/x` and
    `public/../docs/x` are judged as the `docs/x` they resolve to. Absolute
    paths, `../` escapes above the base path, and anything not under an
    enumerated root are all escapes — unknown input is rejected, which is what
    default-deny means.
    """
    stem = target.split("::", 1)[0].split(":", 1)[0].strip()
    if not stem:
        return False
    if stem.startswith("/") or stem.startswith("\\"):
        return True
    normalized = pathlib.PurePosixPath(
        posixpath.normpath(stem.replace("\\", "/"))
    ).as_posix()
    if normalized.startswith("../") or normalized == "..":
        return True
    if normalized in INCLUDE_ALLOWED_FILES:
        return False
    return not normalized.startswith(INCLUDE_ALLOWED_PREFIXES)


def scan_path(path: pathlib.Path) -> list[str]:
    """Findings arising from `path`'s own name (`pub02`)."""
    findings: list[str] = []
    for segment in path.parts:
        for token in INTERNAL_PATH_TOKENS:
            if _token_matches(segment, token):
                findings.append(
                    format_finding(
                        path,
                        1,
                        RULE_INTERNAL_PATH,
                        f"published path names the internal deliverable {token!r}",
                    )
                )
    return findings


def scan_text(text: str, path: pathlib.Path, shingles: frozenset[str]) -> list[str]:
    """Findings for one published file's `text` at `path`.

    The pure-string entrypoint the unit tests drive; `scan_tree` is the
    filesystem entrypoint CI drives. Whole-file findings report line 1.
    """
    findings: list[str] = []

    if shingles:
        for hit in sorted(shingles_of(normalize(text)) & shingles):
            findings.append(
                format_finding(
                    path,
                    1,
                    RULE_SHINGLE,
                    f"reproduces whitepaper body text: {hit!r}",
                )
            )

    findings.extend(scan_path(path))

    for lineno, line in enumerate(text.splitlines(), start=1):
        for figure in _FIGURE_RE.findall(line):
            findings.append(
                format_finding(
                    path,
                    lineno,
                    RULE_INTERNAL_PATH,
                    f"published page cites the whitepaper figure {figure}",
                )
            )

    return findings


def iter_files(root: pathlib.Path) -> list[pathlib.Path]:
    """Every file under `root`, skipping build/VCS noise. Symlinks included."""
    if not root.is_dir():
        return []
    return [
        path
        for path in sorted(root.rglob("*"))
        if not any(part in SKIP_DIRS for part in path.parts)
        and (path.is_file() or path.is_symlink())
    ]


def scan_tree(root: pathlib.Path) -> list[str]:
    """Post-build scan of the rendered tree at `root` (`pub01`, `pub02`)."""
    shingles = whitepaper_shingles()
    findings: list[str] = []
    for path in iter_files(root):
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="ignore")
            findings.extend(scan_text(text, path, shingles))
        else:
            findings.extend(scan_path(path))
    return findings


def scan_prebuild(root: pathlib.Path) -> list[str]:
    """Structural guards over the hand-authored tree (`pub03`, `pub04`)."""
    findings: list[str] = []
    for path in iter_files(root):
        if path.is_symlink():
            findings.append(
                format_finding(
                    path,
                    1,
                    RULE_SYMLINK,
                    "symlink under the pre-build tree; mkdocs copies content",
                )
            )
            continue
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, target in include_targets(text):
            if include_escapes(target):
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_INCLUDE_ESCAPE,
                        "snippet include leaves the permitted roots"
                        f" {INCLUDE_ALLOWED_PREFIXES}: {target!r}",
                    )
                )
    return findings


def self_test_fires() -> bool:
    """Whether the shingle machinery still matches its own source.

    A whitepaper reformat that silently broke normalization would leave a scan
    that passes everything, which is worse than no scan at all.
    """
    text = pathlib.Path(WHITEPAPER).read_text(encoding="utf-8")
    return bool(
        scan_text(text, pathlib.Path(WHITEPAPER), whitepaper_shingles())
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python tools/publish_scan.py",
        description=(
            "D-02 publish-safety gate. Blocking by design (D-20): nonzero exit"
            " on any finding, no exceptions, no non-blocking mode."
        ),
    )
    parser.add_argument(
        "tree",
        nargs="?",
        default=SCANNED_TREE,
        type=pathlib.Path,
        help=f"built tree to scan (default: {SCANNED_TREE})",
    )
    parser.add_argument(
        "--pre-build",
        action="store_true",
        help=f"run the structural guards over {PREBUILD_TREE}/ instead",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.pre_build:
        findings = scan_prebuild(pathlib.Path(PREBUILD_TREE))
    else:
        findings = scan_tree(args.tree)

    for finding in findings:
        print(finding)

    if findings:
        print(
            f"\n{len(findings)} publish-safety violation(s)."
            " Rework the content; there is no exception mechanism (D-20).",
            file=sys.stderr,
        )
        return 1

    if not args.pre_build and not self_test_fires():
        print(
            "publish scan produced zero findings AND failed its own self-test:"
            f" {WHITEPAPER} no longer matches its own shingles. The gate is"
            " dead, not clean.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
