"""PROPOSAL, not ruled: a narrowly pinned historical citation exception (D-IMPL-378 repair 1.5).

Dave, 2026-10-09 10:54 MST: *"Revert the three unauthorized cp-04 citation
edits. Do not loosen its freeze or blanket-exclude frozen examples from citation
checking. Propose a narrowly pinned historical citation exception separately."*

The frozen specimen ``examples/cp-04-corporate-family-tree`` (``D-IMPL-261``;
declared gate CFC-G09, "ZERO files changed") carries three citations of
``SpecDrivenEntityResolution.identity``, a member that never existed. The
specimen may not be edited, so ``cite03`` reports them for ever. This module is
the acceptance of the proposed exception: each of the three is pinned by
(file, line, the exact citation text, the sha256 of the file's text), the
checker keeps exactly those three and counts them, any other dangling citation
-- in cp-04 or anywhere -- still fails, and any change to a pinned file's bytes
voids every pin on that file.
"""

from __future__ import annotations

import hashlib
import pathlib

import pytest

from tools.lints import citations
from tools.lints.citations import RULE_NODE_ID, check_source, repo_index, scan_tree

#: The repo root, from ``tools/lints/tests/<module>.py``.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: The frozen specimen the three pins sit in.
SPECIMEN = "examples/cp-04-corporate-family-tree"

#: The three sites, as the citation checker reported them once ``b7defda9`` was
#: reverted (lane ``378j-cites``, ``20003cee``): (file, line, citation text).
CP04_SITES: list[tuple[str, int, str]] = [
    (f"{SPECIMEN}/deployment.py", 258, "worker.py::SpecDrivenEntityResolution.identity"),
    (f"{SPECIMEN}/deployment.py", 2821, "worker.py::SpecDrivenEntityResolution.identity"),
    (
        f"{SPECIMEN}/projection.py",
        169,
        "src/ccf/assembly/worker.py::SpecDrivenEntityResolution.identity",
    ),
]


def _write(base: pathlib.Path, rel: str, text: str) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sites(findings: list[str]) -> list[str]:
    return sorted(finding.split()[0] for finding in findings)


def test_the_pin_list_is_exactly_the_three_cp04_sites() -> None:
    """Narrow by construction: three entries, each one site, and no other."""
    pins = citations.PINNED_HISTORICAL_CITATIONS
    assert sorted((pin.path, pin.line, pin.citation) for pin in pins) == CP04_SITES
    assert all(pin.reason for pin in pins), pins


def test_the_three_pinned_cp04_citations_are_kept_and_counted() -> None:
    """On this tree, with the specimen untouched: the three are no finding, and
    the scan counts every pin it holds, these three among them, rather than
    dropping one unseen. (Every pin since decision 14 (b) added six:
    ``test_pinned_record_citations.py``.)"""
    scan = scan_tree(REPO_ROOT)
    in_specimen = [f for f in scan.findings if f.startswith(f"{SPECIMEN}/")]
    assert in_specimen == [], in_specimen
    pins = len(citations.PINNED_HISTORICAL_CITATIONS) + len(citations.LINE_TEXT_PINNED_CITATIONS)
    assert scan.pinned_historical == pins, scan


@pytest.mark.parametrize(
    ("host", "text"),
    [
        (f"{SPECIMEN}/fabricated.py", "# `worker.py::SpecDrivenEntityResolution.nope`\n"),
        (f"{SPECIMEN}/README.md", "See `worker.py::SpecDrivenEntityResolution.identity`.\n"),
        (f"{SPECIMEN}/deployment.py", "# `worker.py::SpecDrivenEntityResolution.identity`\n"),
        ("docs/note.md", "See `worker.py::SpecDrivenEntityResolution.identity`.\n"),
    ],
    ids=[
        "a new dangling citation in another cp-04 file",
        "the pinned text in an unpinned cp-04 file",
        "the pinned text at another line of a pinned file",
        "the pinned text outside cp-04",
    ],
)
def test_any_other_dangling_citation_still_fails(host: str, text: str) -> None:
    """Nothing but the three sites is kept: not another cp-04 file, not the
    pinned citation text at any other place."""
    findings = check_source(text, pathlib.Path(host), REPO_ROOT, repo_index(REPO_ROOT))
    assert [finding.split()[1] for finding in findings] == [RULE_NODE_ID], findings


@pytest.mark.parametrize(
    "change",
    ["one byte appended", "a fourth dangling citation added"],
)
def test_a_byte_change_to_a_pinned_file_voids_its_pins(change: str) -> None:
    """The pin is the file's bytes: any change -- one byte, or a fabricated
    fourth dangling citation -- voids every pin on that file, and both pinned
    sites in it are findings again, beside any new one."""
    rel = f"{SPECIMEN}/deployment.py"
    source = (REPO_ROOT / rel).read_text(encoding="utf-8")
    extra = (
        "\n"
        if change == "one byte appended"
        else "# `worker.py::SpecDrivenEntityResolution.nope`\n"
    )
    changed = source + extra
    findings = check_source(changed, pathlib.Path(rel), REPO_ROOT, repo_index(REPO_ROOT))
    expected = [f"{rel}:258", f"{rel}:2821"]
    if change != "one byte appended":
        expected.append(f"{rel}:{changed.count(chr(10))}")
    assert _sites(findings) == sorted(expected), findings


def test_a_pin_keeps_only_its_own_site(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The key is (file, line, citation text, file hash), all four: the same
    citation on the next line, and another dead citation in the same file, are
    findings beside the one pinned site."""
    _write(tmp_path, "src/pkg/mod.py", "class A:\n    def m(self) -> None: ...\n")
    note = (
        "See `src/pkg/mod.py::A.gone`.\n"
        "See `src/pkg/mod.py::A.gone`.\n"
        "See `src/pkg/mod.py::A.other`.\n"
    )
    _write(tmp_path, "docs/note.md", note)
    pin = citations.PinnedCitation(
        path="docs/note.md",
        line=1,
        citation="src/pkg/mod.py::A.gone",
        sha256=hashlib.sha256(note.encode("utf-8")).hexdigest(),
        reason="a test pin",
    )
    monkeypatch.setattr(citations, "PINNED_HISTORICAL_CITATIONS", (pin,))
    scan = scan_tree(tmp_path)
    assert _sites(scan.findings) == ["docs/note.md:2", "docs/note.md:3"], scan
    assert scan.pinned_historical == 1, scan
