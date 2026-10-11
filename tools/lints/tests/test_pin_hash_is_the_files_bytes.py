"""D-IMPL-378, Dave 2026-10-09 20:22 MST: a file-hash pin is the file's raw bytes.

Decision 13 (a) (16:38 MST; Grok's text, which Dave adopted): *"(a) Accept the
cp-04 pins, locked to the file’s bytes."* As built, a file-hash pin hashed the
text the checker decodes (``read_text(encoding="utf-8", errors="replace")``,
with universal newlines), so a copy of a pinned file whose bytes differ but
whose text reads alike, such as Windows line endings or an invalid byte
replaced by another, still matched its pin. Dave's answer, verbatim:
*"(b). The ruling was bytes, and the page already says a change to any byte
voids the pin. Do not rewrite the page to match the looser check."* *"Hash the
raw bytes. Windows line endings are different bytes, so they fail the pin. It
stays a tooling change in this batch, and the `cp-04` freeze gate is
unchanged."*

Asserted through the gate's own path, over trees written to disk:
``tools/lints/citations.py::scan_tree`` and ``python -m tools.lints
--citations``. Both the real pins (the four files that hold the seven
file-hash pins, copied with the files their pinned citations name) and a
fixture pin are exercised. And fail closed: text handed to
``tools/lints/citations.py::check_source`` alone keeps no file-hash pin. The
roadmap's two pins, keyed on their line's text (question 3 (ii), 17:53 MST),
are not file-hash pins; the last test shows they are untouched.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys
from collections.abc import Callable

import pytest

from tools.lints import citations
from tools.lints.citations import (
    LINE_TEXT_PINNED_CITATIONS,
    PINNED_HISTORICAL_CITATIONS,
    RULE_NODE_ID,
    check_source,
    repo_index,
    resolve_cited,
    scan_tree,
)

#: The repo root, from ``tools/lints/tests/<module>.py``.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: The four files that hold the seven file-hash pins (decision 13 (a)'s three,
#: decision 14 (b)'s four), with how many pins each holds.
PINNED_FILES: dict[str, int] = {
    "docs/surface-changes/16-24-experience-door-entitlement.md": 3,
    "examples/cp-04-corporate-family-tree/deployment.py": 2,
    "examples/cp-04-corporate-family-tree/projection.py": 1,
    "tests/examples/test_cp_04_debt.py": 1,
}

ROADMAP = ".planning/ROADMAP.md"


@pytest.fixture(scope="module")
def index() -> dict[str, list[str]]:
    return repo_index(REPO_ROOT)


def _site(finding: str) -> str:
    return finding.split()[0]


def _sites(rel: str) -> list[str]:
    """The pinned sites in `rel`, as ``path:line``."""
    return sorted(
        f"{pin.path}:{pin.line}" for pin in PINNED_HISTORICAL_CITATIONS if pin.path == rel
    )


def _windows(raw: bytes) -> bytes:
    """`raw` with Windows line endings: other bytes, the same decoded text."""
    return raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def _as_is(raw: bytes) -> bytes:
    return raw


def _copy_with_targets(
    root: pathlib.Path,
    rel: str,
    transform: Callable[[bytes], bytes],
    index: dict[str, list[str]],
) -> None:
    """Write `rel` (its bytes through `transform`) and, as they are, the files
    its pinned citations name, into the tree at `root`."""
    copies = {rel: transform((REPO_ROOT / rel).read_bytes())}
    for pin in PINNED_HISTORICAL_CITATIONS:
        if pin.path != rel:
            continue
        target, _ambiguous = resolve_cited(pin.citation.split("::", 1)[0], REPO_ROOT, index)
        assert target is not None, pin
        copies.setdefault(target.relative_to(REPO_ROOT).as_posix(), target.read_bytes())
    for path, raw in copies.items():
        dst = root / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw)


def _gate(root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    """The citation gate as CI runs it, over the tree at `root`."""
    return subprocess.run(
        [sys.executable, "-m", "tools.lints", "--citations", "--base", str(root)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_the_pinned_files_are_these_four() -> None:
    """Control: the parametrization below covers every file-hash pin."""
    files = sorted({pin.path for pin in PINNED_HISTORICAL_CITATIONS})
    held = {rel: len(_sites(rel)) for rel in files}
    assert held == PINNED_FILES, held


# --- the real pins, through the scan over a tree on disk ---------------------------


@pytest.mark.parametrize("rel", sorted(PINNED_FILES))
def test_a_pinned_file_with_windows_line_endings_voids_its_pins_in_the_scan(
    rel: str, tmp_path: pathlib.Path, index: dict[str, list[str]]
) -> None:
    """As it is, the copy keeps its pins; with Windows line endings (other
    bytes, the same text) it keeps none, and each pinned site is a finding."""
    sites = _sites(rel)
    as_is, windows = tmp_path / "as-is", tmp_path / "windows"
    _copy_with_targets(as_is, rel, _as_is, index)
    _copy_with_targets(windows, rel, _windows, index)
    assert (windows / rel).read_bytes() != (as_is / rel).read_bytes()
    assert (windows / rel).read_text(encoding="utf-8", errors="replace") == (
        as_is / rel
    ).read_text(encoding="utf-8", errors="replace"), "the copies must read alike"

    kept = scan_tree(as_is)
    assert [finding for finding in kept.findings if _site(finding) in sites] == [], kept
    assert kept.pinned_historical == len(sites), kept

    voided = scan_tree(windows)
    assert sorted(_site(finding) for finding in voided.findings) == sites, voided.findings
    assert {finding.split()[1] for finding in voided.findings} == {RULE_NODE_ID}, voided.findings
    assert voided.pinned_historical == 0, voided


def test_the_gate_command_fails_a_tree_whose_pinned_files_have_windows_line_endings(
    tmp_path: pathlib.Path, index: dict[str, list[str]]
) -> None:
    """``python -m tools.lints --citations`` over a tree on disk: rc 0 with the
    four pinned files as they are; rc 1 with Windows line endings, naming every
    one of the seven pinned sites."""
    for rel in PINNED_FILES:
        _copy_with_targets(tmp_path / "as-is", rel, _as_is, index)
        _copy_with_targets(tmp_path / "windows", rel, _windows, index)
    as_is = _gate(tmp_path / "as-is")
    assert as_is.returncode == 0, as_is.stdout + as_is.stderr
    windows = _gate(tmp_path / "windows")
    assert windows.returncode == 1, windows.stdout + windows.stderr
    reported = sorted(line.split()[0] for line in windows.stdout.splitlines() if line.strip())
    assert reported == sorted(site for rel in PINNED_FILES for site in _sites(rel)), windows.stdout


# --- a fixture pin: three ways bytes can differ while the text reads alike ---------

#: The pinned bytes and a copy that decodes to the same text, per case.
ALIKE: dict[str, tuple[bytes, bytes]] = {
    "Windows line endings": (
        b"See `src/pkg/mod.py::A.gone`.\n",
        b"See `src/pkg/mod.py::A.gone`.\r\n",
    ),
    "a lone carriage return": (
        b"See `src/pkg/mod.py::A.gone`.\n",
        b"See `src/pkg/mod.py::A.gone`.\r",
    ),
    "an invalid byte replaced by another invalid byte": (
        b"See `src/pkg/mod.py::A.gone`. \xff\n",
        b"See `src/pkg/mod.py::A.gone`. \xfe\n",
    ),
}


@pytest.mark.parametrize("case", sorted(ALIKE))
def test_bytes_that_read_alike_do_not_keep_a_fixture_pin(
    case: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pin on a file's bytes keeps that file, and keeps nothing once a byte
    changes, even where the decoded text reads the same (the invalid bytes
    0xFF and 0xFE both decode to U+FFFD)."""
    pinned, alike = ALIKE[case]
    (tmp_path / "src/pkg").mkdir(parents=True)
    (tmp_path / "src/pkg/mod.py").write_bytes(b"class A:\n    def m(self) -> None: ...\n")
    (tmp_path / "docs").mkdir()
    note = tmp_path / "docs/note.md"
    pin = citations.PinnedCitation(
        path="docs/note.md",
        line=1,
        citation="src/pkg/mod.py::A.gone",
        sha256=hashlib.sha256(pinned).hexdigest(),
        reason="a test pin",
    )
    monkeypatch.setattr(citations, "PINNED_HISTORICAL_CITATIONS", (pin,))
    monkeypatch.setattr(citations, "LINE_TEXT_PINNED_CITATIONS", ())

    note.write_bytes(pinned)
    text = note.read_text(encoding="utf-8", errors="replace")
    kept = scan_tree(tmp_path)
    assert kept.findings == [] and kept.pinned_historical == 1, kept

    note.write_bytes(alike)
    assert note.read_text(encoding="utf-8", errors="replace") == text, "the case must read alike"
    voided = scan_tree(tmp_path)
    assert [_site(finding) for finding in voided.findings] == ["docs/note.md:1"], voided
    assert voided.pinned_historical == 0, voided


# --- the gate reads a file's bytes once and decodes them as read_text does -------

#: Byte strings whose decoding differs between a plain ``bytes.decode`` and
#: ``read_text`` (line endings), or that exercise the replacement path.
DECODE_CASES: dict[str, bytes] = {
    "LF": b"a\nb\n",
    "Windows line endings": b"a\r\nb\r\n",
    "a lone carriage return": b"a\rb\r",
    "mixed line endings": b"a\r\nb\rc\n",
    "invalid bytes": b"a\xffb\xfe\n",
    "a truncated multibyte sequence": b"a\xe2\x80",
    "a byte-order mark": b"\xef\xbb\xbfa\n",
    "empty": b"",
}


@pytest.mark.parametrize("case", sorted(DECODE_CASES))
def test_the_gate_decodes_a_file_s_bytes_as_read_text_does(
    case: str, tmp_path: pathlib.Path
) -> None:
    """``check_file_bytes`` claims its findings are ``check_source``'s on the
    text ``read_text`` gives: the decoding it uses must give that text."""
    raw = DECODE_CASES[case]
    path = tmp_path / "file"
    path.write_bytes(raw)
    assert citations._decoded(raw) == path.read_text(encoding="utf-8", errors="replace")


# --- fail closed: text alone keeps no file-hash pin --------------------------------


@pytest.mark.parametrize("rel", sorted(PINNED_FILES))
def test_text_alone_keeps_no_file_hash_pin(rel: str, index: dict[str, list[str]]) -> None:
    """A caller that hands ``check_source`` only the text cannot show the
    bytes a pin is, so each pinned site in that text is a finding."""
    text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
    findings = check_source(text, pathlib.Path(rel), REPO_ROOT, index)
    assert sorted(_site(finding) for finding in findings) == _sites(rel), findings


# --- control: the roadmap's line-text pins are not file-hash pins ------------------


def test_the_roadmap_line_text_pins_still_key_on_the_line_s_text(
    tmp_path: pathlib.Path, index: dict[str, list[str]]
) -> None:
    """Control (question 3 (ii)): the roadmap with Windows line endings keeps
    both line-text pins; a line ending is not part of the line's text."""
    assert {pin.path for pin in LINE_TEXT_PINNED_CITATIONS} == {ROADMAP}
    copies = {ROADMAP: _windows((REPO_ROOT / ROADMAP).read_bytes())}
    for pin in LINE_TEXT_PINNED_CITATIONS:
        target, _ambiguous = resolve_cited(pin.citation.split("::", 1)[0], REPO_ROOT, index)
        assert target is not None, pin
        copies[target.relative_to(REPO_ROOT).as_posix()] = target.read_bytes()
    for path, raw in copies.items():
        dst = tmp_path / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw)
    scan = scan_tree(tmp_path)
    at_roadmap = [finding for finding in scan.findings if _site(finding).startswith(f"{ROADMAP}:")]
    assert at_roadmap == [], at_roadmap
    assert scan.pinned_historical == len(LINE_TEXT_PINNED_CITATIONS), scan
