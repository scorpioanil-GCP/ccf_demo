# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""D-IMPL-378 decision 14 (b): the review record exempted, the other six citations pinned.

Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation, decision 14:
*"(b) Exempt the dated records. Pin the rest. Do not edit records in place."*
Option (b) as lane ``378j-cites`` wrote it (its report, proposal P-3): declare
``docs/D-IMPL-353-CLOSE-REVIEWS.md`` a dated record in
``tools/lints/citations.py::HISTORICAL_RECORDS``, the C6 (c) precedent, and pin
the other six. Repair 1.7 made all nine ``cite03`` findings. Each is a bare
citation of a function nested in another function, in text that may not be
edited: the review record, whose own header keeps it unedited; a roadmap
success criterion that quotes what four docstrings cited before ``D-IMPL-192``;
a landed surface-change fragment; and a test of the frozen cp-04 specimen.

The keying, Dave, 2026-10-09 17:53 MST (*"Four questions use
recommendations"*, question 3 (ii)): the roadmap's two pins are keyed on the
citing line's full text and the citation's text, not on the line's number or
the file's hash. An edit elsewhere in ``.planning/ROADMAP.md``, even one that
moves the line, leaves them valid; any edit to that line voids them; and a
pinned line text that stands on more than one line of the file keeps nothing.
Every other pin keeps the file's hash: decision 13 (a)'s three cp-04 pins
(*"locked to the file’s bytes"*), the landed fragment's three and the frozen
test's one.

Every property is asserted behaviorally, through the shipped
``tools/lints/citations.py::check_source``,
``tools/lints/citations.py::check_file_bytes`` and
``tools/lints/citations.py::scan_tree``, on the real files, on edited copies of
their text and, for the hash key's owed test, on one fixture tree under
pytest's ``tmp_path``; nothing here writes to the repository. Derived from the
module of this name on ``proposal-378j-record-citations`` at ``85f52dd9``,
which pinned all nine on the file's hash: the three review-record pins are
dropped, the roadmap's keying is replaced, and each roadmap property has its
own test.
"""

from __future__ import annotations

import hashlib
import pathlib
from collections.abc import Callable

import pytest

from tools.lints import citations
from tools.lints.citations import (
    RULE_NODE_ID,
    Scan,
    check_file_bytes,
    check_source,
    exemption_reason,
    repo_index,
    scan_tree,
)

#: The repo root, from ``tools/lints/tests/<module>.py``.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: The dated record decision 14 (b) exempts.
REVIEW_RECORD = "docs/D-IMPL-353-CLOSE-REVIEWS.md"

#: Its three findings at the base ``d128a30d``: (file, line, citation text).
REVIEW_RECORD_SITES: list[tuple[str, int, str]] = [
    (REVIEW_RECORD, 72, "runtime/ccf_runtime/http_api/routes/agent.py::declarations"),
    (REVIEW_RECORD, 73, "runtime/ccf_runtime/http_api/routes/skill.py::catalog"),
    (REVIEW_RECORD, 74, "runtime/ccf_runtime/http_api/routes/config.py::keys"),
]

FRAGMENT = "docs/surface-changes/16-24-experience-door-entitlement.md"
FROZEN_TEST = "tests/examples/test_cp_04_debt.py"
ROADMAP = ".planning/ROADMAP.md"

#: The four citations pinned on the file's hash: (file, line, citation text).
HASH_PINNED_SITES: list[tuple[str, int, str]] = [
    (FRAGMENT, 28, "runtime/ccf_runtime/mcp/experience.py::get_context"),
    (FRAGMENT, 162, "tests/crossproc/servers/mcp_experience_child.py::read_replay_record"),
    (FRAGMENT, 164, "examples/external/00-hello-context/serve.py::replay_record_reader"),
    (FROZEN_TEST, 824, "runtime/ccf_runtime/http_api/routes/product.py::retrieve"),
]

#: The two citations pinned on the citing line's text. Both stand on one line of
#: the roadmap (line 2242 at the base); the pins do not key on its number, so
#: the tests find the line by its content.
ROADMAP_CITATIONS: tuple[str, ...] = (
    "examples/04-cross-process/producer_child.py::resolve",
    "examples/external/00-hello-context/serve.py::context_provider",
)

#: Decision 13 (a)'s three cp-04 pins, counted beside these six, and the
#: frozen specimen they stand in.
CP04_PIN_COUNT = 3
CP04_SPECIMEN = "examples/cp-04-corporate-family-tree/"


@pytest.fixture(scope="module")
def index() -> dict[str, list[str]]:
    return repo_index(REPO_ROOT)


@pytest.fixture(scope="module")
def real_scan() -> Scan:
    return scan_tree(REPO_ROOT)


def _site(finding: str) -> str:
    """``path:line`` of a finding."""
    return finding.split()[0]


def _file(finding: str) -> str:
    return _site(finding).rsplit(":", 1)[0]


def _cited(finding: str) -> str:
    """The citation text a ``cite03`` finding reports."""
    return finding.split(" cites ", 1)[1].split(", but ", 1)[0]


def _check(rel: str, text: str, index: dict[str, list[str]]) -> list[str]:
    """``check_source`` on `text`, attributed to `rel` in the real tree."""
    return check_source(text, pathlib.Path(rel), REPO_ROOT, index)


def _check_bytes(rel: str, raw: bytes, index: dict[str, list[str]]) -> list[str]:
    """``check_file_bytes`` on `raw`, attributed to `rel` in the real tree: the
    gate's path, the only one on which a file-hash pin can be kept."""
    return check_file_bytes(raw, pathlib.Path(rel), REPO_ROOT, index)


def _roadmap() -> tuple[list[str], int]:
    """The roadmap's lines (ends kept) and the index of the one holding both."""
    lines = (REPO_ROOT / ROADMAP).read_text(encoding="utf-8").splitlines(keepends=True)
    holding = [i for i, line in enumerate(lines) if all(c in line for c in ROADMAP_CITATIONS)]
    assert len(holding) == 1, f"the two citations stand on {len(holding)} roadmap lines"
    assert lines[-1].endswith("\n"), "the roadmap no longer ends with a newline"
    return lines, holding[0]


def _roadmap_findings(lines: list[str], index: dict[str, list[str]]) -> list[str]:
    """The findings on the two pinned citations, as ``"<line> <citation>"``."""
    return sorted(
        f"{_site(finding).rsplit(':', 1)[1]} {_cited(finding)}"
        for finding in _check(ROADMAP, "".join(lines), index)
        if finding.split()[1] == RULE_NODE_ID and _cited(finding) in ROADMAP_CITATIONS
    )


def _both_at(*line_numbers: int) -> list[str]:
    return sorted(f"{n} {c}" for n in line_numbers for c in ROADMAP_CITATIONS)


# --- the review record: a dated record, exempt -----------------------------------


def test_the_review_record_is_exempt_by_the_entry_that_names_decision_14b() -> None:
    """Exempt by an entry naming the file and the ruling, not by a broader
    pattern that happens to match it (the C6 (c) test's discipline)."""
    reason = exemption_reason(REVIEW_RECORD)
    assert reason is not None, (
        f"{REVIEW_RECORD} is gated; D-IMPL-378 decision 14 (b) exempts it as a dated record"
    )
    assert REVIEW_RECORD in citations.HISTORICAL_RECORDS, (
        f"{REVIEW_RECORD} is exempt by a broader pattern, not by its own entry"
    )
    assert "D-IMPL-378" in reason and "14 (b)" in reason, (
        f"{REVIEW_RECORD} is exempt by a reason that does not name D-IMPL-378 decision 14 (b):"
        f" {reason!r}"
    )


def test_the_files_holding_the_six_stay_gated() -> None:
    """Control: "Pin the rest" -- the six are kept one by one, never by
    exempting the files they stand in."""
    for rel in (ROADMAP, FRAGMENT, FROZEN_TEST):
        assert exemption_reason(rel) is None, (
            f"{rel} is exempt; decision 14 (b) pins its citations instead"
        )


def test_the_review_record_holds_no_finding_on_this_tree(real_scan: Scan) -> None:
    """Its three citations are findings at the base and must not be."""
    at_record = [finding for finding in real_scan.findings if _file(finding) == REVIEW_RECORD]
    assert at_record == [], at_record


# --- the six: kept as pins, and counted --------------------------------------------


def test_the_four_hash_pinned_citations_are_kept_on_this_tree(real_scan: Scan) -> None:
    sites = {f"{path}:{line}" for path, line, _citation in HASH_PINNED_SITES}
    not_kept = [finding for finding in real_scan.findings if _site(finding) in sites]
    assert not_kept == [], not_kept


def test_the_two_roadmap_citations_are_kept_on_this_tree(real_scan: Scan) -> None:
    not_kept = [
        finding
        for finding in real_scan.findings
        if _file(finding) == ROADMAP and _cited(finding) in ROADMAP_CITATIONS
    ]
    assert not_kept == [], not_kept


def test_every_pin_is_counted_on_this_tree(real_scan: Scan) -> None:
    """Kept, never dropped unseen: the scan counts decision 13 (a)'s three and
    these six, and the exempt record's three are not among them."""
    expected = CP04_PIN_COUNT + len(HASH_PINNED_SITES) + len(ROADMAP_CITATIONS)
    assert real_scan.pinned_historical == expected, real_scan


def test_the_pin_lists_are_exactly_these_nine_sites() -> None:
    """Narrow by construction, across both lists: on the file's hash, decision
    13 (a)'s three cp-04 sites and these four; on the line's text, the
    roadmap's two, on the one line that holds them; each pin with its reason,
    every decision 14 (b) pin naming that ruling; no pin for the exempt
    record; and no file pinned both ways."""
    hash_pins = sorted(
        (pin.path, pin.line, pin.citation) for pin in citations.PINNED_HISTORICAL_CITATIONS
    )
    specimen = [site for site in hash_pins if site[0].startswith(CP04_SPECIMEN)]
    assert len(specimen) == CP04_PIN_COUNT, specimen
    assert [site for site in hash_pins if site not in specimen] == sorted(HASH_PINNED_SITES)
    line_pins = citations.LINE_TEXT_PINNED_CITATIONS
    assert sorted((pin.path, pin.citation) for pin in line_pins) == sorted(
        (ROADMAP, citation) for citation in ROADMAP_CITATIONS
    )
    lines, at = _roadmap()
    assert all(pin.line_text == lines[at].removesuffix("\n") for pin in line_pins), line_pins
    every = [*citations.PINNED_HISTORICAL_CITATIONS, *line_pins]
    assert all(pin.reason for pin in every), every
    ruled = [pin for pin in every if not pin.path.startswith(CP04_SPECIMEN)]
    assert all("D-IMPL-378 decision 14 (b)" in pin.reason for pin in ruled), ruled
    assert not any(pin.path == REVIEW_RECORD for pin in every), every
    both_ways = {pin.path for pin in citations.PINNED_HISTORICAL_CITATIONS} & {
        pin.path for pin in line_pins
    }
    assert both_ways == set(), both_ways


# --- the hash-keyed four: a byte change voids every pin on the file ----------------


@pytest.mark.parametrize("rel", sorted({path for path, _line, _citation in HASH_PINNED_SITES}))
def test_a_byte_change_to_a_hash_pinned_file_voids_its_pins(
    rel: str, index: dict[str, list[str]]
) -> None:
    """The file's bytes, as for the cp-04 pins: the untouched file's bytes keep
    its pinned sites, and one byte appended makes each of them a finding again.
    Through ``check_file_bytes``, because text alone keeps no file-hash pin."""
    raw = (REPO_ROOT / rel).read_bytes()
    pinned = sorted(f"{path}:{line}" for path, line, _citation in HASH_PINNED_SITES if path == rel)
    untouched = [_site(finding) for finding in _check_bytes(rel, raw, index)]
    assert [site for site in untouched if site in pinned] == [], untouched
    changed = _check_bytes(rel, raw + b"\n", index)
    assert sorted(_site(finding) for finding in changed) == pinned, changed


@pytest.mark.parametrize(
    ("host", "text"),
    [
        ("docs/note.md", "See `runtime/ccf_runtime/mcp/experience.py::get_context`.\n"),
        (FRAGMENT, "See `runtime/ccf_runtime/mcp/experience.py::get_context`.\n"),
        (FROZEN_TEST, "# `runtime/ccf_runtime/http_api/routes/product.py::retrieve`\n"),
        (ROADMAP, "See `examples/04-cross-process/producer_child.py::resolve`.\n"),
    ],
    ids=[
        "a fragment pin's citation outside its file",
        "a fragment pin's citation in a changed copy of its file",
        "the frozen test pin's citation in a changed copy of its file",
        "a roadmap pin's citation on a line that is not the pinned line",
    ],
)
def test_a_pinned_citation_anywhere_else_still_fails(
    host: str, text: str, index: dict[str, list[str]]
) -> None:
    """Control: a pin keeps its own site and nothing else."""
    findings = _check(host, text, index)
    assert [finding.split()[1] for finding in findings] == [RULE_NODE_ID], findings


# --- the roadmap's two: keyed on the line's text and the citation's text -----------


def test_the_untouched_roadmap_keeps_both(index: dict[str, list[str]]) -> None:
    lines, _at = _roadmap()
    assert _roadmap_findings(lines, index) == []


#: Edits elsewhere in the roadmap: two move the pinned line, two do not; all
#: four change the file's hash.
EDITS_ELSEWHERE: dict[str, Callable[[list[str], int], list[str]]] = {
    "a line inserted above it, which moves it down": (
        lambda lines, at: lines[:at] + ["An inserted line.\n"] + lines[at:]
    ),
    "a line deleted above it, which moves it up": lambda lines, at: lines[: at - 1] + lines[at:],
    "the line above it edited, which moves nothing": (
        lambda lines, at: lines[: at - 1] + [lines[at - 1][:-1] + " Edited.\n"] + lines[at:]
    ),
    "a line appended at the end of the file": lambda lines, at: lines + ["An appended line.\n"],
}


@pytest.mark.parametrize("edit", sorted(EDITS_ELSEWHERE))
def test_an_edit_elsewhere_in_the_roadmap_leaves_both_pins_valid(
    edit: str, index: dict[str, list[str]]
) -> None:
    """Not the line's number, not the file's hash: the line may move."""
    lines, at = _roadmap()
    changed = EDITS_ELSEWHERE[edit](lines, at)
    assert changed != lines
    holding = [i for i, line in enumerate(changed) if line == lines[at]]
    assert len(holding) == 1, holding
    assert (holding[0] != at) == ("moves it" in edit), (edit, at, holding)
    assert _roadmap_findings(changed, index) == [], edit


#: Edits to the pinned line itself; each keeps both citations on it.
EDITS_TO_THE_LINE: dict[str, Callable[[str], str]] = {
    "one character appended": lambda line: line[:-1] + ".\n",
    "a word changed": lambda line: line.replace("**diff-empty**", "**diff-clean**", 1),
    "trailing whitespace added": lambda line: line[:-1] + " \n",
    "re-indented by one space": lambda line: " " + line,
}


@pytest.mark.parametrize("edit", sorted(EDITS_TO_THE_LINE))
def test_any_edit_to_the_pinned_roadmap_line_voids_both_pins(
    edit: str, index: dict[str, list[str]]
) -> None:
    """The untouched line keeps both; the edited line keeps neither."""
    lines, at = _roadmap()
    assert _roadmap_findings(lines, index) == [], "the untouched line keeps both"
    edited_line = EDITS_TO_THE_LINE[edit](lines[at])
    assert edited_line != lines[at]
    assert all(citation in edited_line for citation in ROADMAP_CITATIONS), edit
    edited = lines[:at] + [edited_line] + lines[at + 1 :]
    assert _roadmap_findings(edited, index) == _both_at(at + 1), edit


#: A second copy of the pinned line, placed three ways.
COPIES: dict[str, Callable[[list[str], int], list[str]]] = {
    "copied directly below it": lambda lines, at: lines[: at + 1] + [lines[at]] + lines[at + 1 :],
    "copied to the top of the file": lambda lines, at: [lines[at]] + lines,
    "copied to the end of the file": lambda lines, at: lines + [lines[at]],
}


@pytest.mark.parametrize("copy", sorted(COPIES))
def test_a_pinned_roadmap_line_standing_on_two_lines_keeps_nothing(
    copy: str, index: dict[str, list[str]]
) -> None:
    """The pin cannot say which copy it means, so it keeps neither."""
    lines, at = _roadmap()
    assert _roadmap_findings(lines, index) == [], "the untouched line keeps both"
    copied = COPIES[copy](lines, at)
    holding = [i + 1 for i, line in enumerate(copied) if line == lines[at]]
    assert len(holding) == 2, holding
    assert _roadmap_findings(copied, index) == _both_at(*holding), copy


def test_the_pinned_roadmap_line_in_another_file_keeps_nothing(
    index: dict[str, list[str]]
) -> None:
    """Control: the file is part of the key."""
    lines, at = _roadmap()
    findings = _check("docs/note.md", lines[at], index)
    assert sorted(_cited(finding) for finding in findings) == sorted(ROADMAP_CITATIONS), findings


# --- the owed key test: the citation's text is part of both keys -----------------


def test_a_hash_pinned_line_with_two_dangling_citations_keeps_only_the_pinned_one(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owed by the coordinator's certification of decision 13 (a): with the
    citation's text taken out of the hash pin's key, every lint test stayed
    green, because no test put two dangling citations on one pinned line.
    Here one line holds two and only one is pinned; the other stays a
    finding."""
    (tmp_path / "src/pkg").mkdir(parents=True)
    (tmp_path / "src/pkg/mod.py").write_text(
        "class A:\n    def m(self) -> None: ...\n", encoding="utf-8"
    )
    note = "See `src/pkg/mod.py::A.gone` and `src/pkg/mod.py::A.lost`.\n"
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/note.md").write_text(note, encoding="utf-8")
    pin = citations.PinnedCitation(
        path="docs/note.md",
        line=1,
        citation="src/pkg/mod.py::A.gone",
        sha256=hashlib.sha256((tmp_path / "docs/note.md").read_bytes()).hexdigest(),
        reason="a test pin",
    )
    monkeypatch.setattr(citations, "PINNED_HISTORICAL_CITATIONS", (pin,))
    monkeypatch.setattr(citations, "LINE_TEXT_PINNED_CITATIONS", ())
    scan = scan_tree(tmp_path)
    found = [(_site(finding), _cited(finding)) for finding in scan.findings]
    assert found == [("docs/note.md:1", "src/pkg/mod.py::A.lost")], scan
    assert scan.pinned_historical == 1, scan


def test_a_line_text_pinned_line_with_two_dangling_citations_keeps_only_the_pinned_one(
    monkeypatch: pytest.MonkeyPatch, index: dict[str, list[str]]
) -> None:
    """The same for the line's-text key: the roadmap's line holds both pinned
    citations; with only the first one pinned, the second is a finding."""
    first, second = ROADMAP_CITATIONS
    only = tuple(pin for pin in citations.LINE_TEXT_PINNED_CITATIONS if pin.citation == first)
    assert len(only) == 1, only
    monkeypatch.setattr(citations, "LINE_TEXT_PINNED_CITATIONS", only)
    lines, at = _roadmap()
    assert _roadmap_findings(lines, index) == [f"{at + 1} {second}"]
