"""Controls over `tools/estate_census/evidence.py` — the exact-evidence half of
`D-IMPL-358` ruling 8.

The table in `tools/estate_census/evidence.py::census_outcome` was MEASURED
against pytest 9.1.1, not reasoned about, and three of its rows contradict the
natural reading. Those three rows are the reason this module exists:

* a declared skip emits **no ``call`` report at all**, so code keyed on
  ``when == "call"`` loses every ``@pytest.mark.skip`` node;
* a teardown failure is an **error** and arrives on a node whose ``call`` already
  reported ``passed`` — pytest itself counts such a node once as a pass and once
  as an error;
* an xfail reports ``skipped`` and an xpass reports ``passed``, separated only by
  ``report.wasxfail``, while a **strict** xpass reports a plain ``failed``.

**The positive control is `test_the_measured_pytest_report_table_is_reproduced_exactly`**,
which asserts every row of that table. If the translation drifts, it fails here
rather than silently reclassifying a teardown error as a pass.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tools.estate_census.evidence import (
    BUNDLE_KIND,
    BUNDLE_VERSION,
    RED_OUTCOMES,
    Counts,
    NodeOutcome,
    PhaseReport,
    build,
    census_outcome,
    credential_in_file,
    read_json,
    read_json_with_reason,
    write_json,
    write_junit_xml,
)

#: The table as MEASURED, one row per observed pytest report shape.
#: ``(when, pytest outcome, wasxfail) -> census outcome``
MEASURED_TABLE: tuple[tuple[str, str, bool, str | None], ...] = (
    ("setup", "passed", False, None),
    ("call", "passed", False, "passed"),
    ("teardown", "passed", False, None),
    ("call", "failed", False, "failed"),
    ("setup", "failed", False, "error"),
    ("teardown", "failed", False, "error"),
    ("setup", "skipped", False, "skipped"),
    ("call", "skipped", False, "skipped"),
    ("call", "skipped", True, "xfailed"),
    ("call", "passed", True, "xpassed"),
)


def test_the_measured_pytest_report_table_is_reproduced_exactly() -> None:
    """THE POSITIVE CONTROL for the whole module."""
    wrong = [
        f"{when}/{outcome}/wasxfail={was} -> {census_outcome(when, outcome, was)!r}, want {want!r}"
        for when, outcome, was, want in MEASURED_TABLE
        if census_outcome(when, outcome, was) != want
    ]
    assert not wrong, "\n".join(wrong)


def test_a_declared_skip_is_captured_even_though_it_emits_no_call_report() -> None:
    """The measured shape is ``setup/skipped`` then ``teardown/passed``, with no
    ``call`` report at all."""
    assert census_outcome("setup", "skipped", False) == "skipped"
    node = NodeOutcome.rolled_up(
        "t.py::s", (PhaseReport("setup", "skipped"), PhaseReport("teardown", "passed"))
    )
    assert node.outcome == "skipped"


def test_a_teardown_error_on_a_passing_call_rolls_up_to_error_not_pass() -> None:
    """pytest counts such a node once as a pass and once as an error. A mapping of
    node id to a single outcome would keep whichever arrived last."""
    node = NodeOutcome.rolled_up(
        "t.py::x",
        (
            PhaseReport("setup", census_outcome("setup", "passed", False) or "passed"),
            PhaseReport("call", census_outcome("call", "passed", False) or ""),
            PhaseReport("teardown", census_outcome("teardown", "failed", False) or ""),
        ),
    )
    assert node.outcome == "error"
    assert node.is_red
    assert [phase.outcome for phase in node.phases] == ["passed", "passed", "error"]


def test_the_phase_reports_are_preserved_and_not_only_the_roll_up() -> None:
    """`phases` is the evidence; `outcome` is a reading of it. Discarding the
    phases would make "passed its call, raised in teardown" unrecoverable."""
    node = NodeOutcome.rolled_up(
        "t.py::x", (PhaseReport("call", "passed"), PhaseReport("teardown", "error"))
    )
    assert len(node.phases) == 2
    assert node.as_dict()["phases"] == [
        {"when": "call", "outcome": "passed", "detail": ""},
        {"when": "teardown", "outcome": "error", "detail": ""},
    ]


def test_only_failed_and_error_are_red() -> None:
    """Widening this set would turn every quarantined known gap into a new red on
    the first census; narrowing it would hide a real failure."""
    assert RED_OUTCOMES == frozenset({"failed", "error"})


def test_the_six_counts_are_independent_tallies_over_the_roster() -> None:
    """Four numbers plus the two that must stay out of all four. ``passed`` is
    never derived as ``tests - failures - skipped - errors``: that arithmetic is
    wrong whenever one node owns two outcomes."""
    outcomes = {
        f"t.py::n{i}": NodeOutcome.rolled_up(f"t.py::n{i}", (PhaseReport("call", outcome),))
        for i, outcome in enumerate(
            ["passed", "passed", "failed", "error", "skipped", "xfailed", "xpassed"]
        )
    }
    counts = Counts.over(outcomes)
    assert counts.as_dict() == {
        "passed": 2, "failed": 1, "errors": 1, "skipped": 1, "xfailed": 1, "xpassed": 1
    }


def test_build_redacts_every_free_text_field_before_anything_is_serialized() -> None:
    """A bundle that exists is a bundle that was redacted — no code path can
    serialize an unredacted value, because redaction happens on the way in."""
    secret = "Sup3r-S3cr3t-Pa55"
    bundle = build(
        provenance={"dsn": f"postgresql://ccf:{secret}@192.168.4.76/ccf_v2", "exit_status": 1},
        estate_before={"s": {"position": {"t": 1}}},
        estate_after={"s": {"position": {"t": 1}}},
        collected=("t.py::a",),
        phase_reports={
            "t.py::a": (
                PhaseReport("call", "failed", f"host=h user=u password={secret} dbname=d"),
            )
        },
        collection_errors=({"nodeid": "t.py", "detail": f"Bearer {secret}"},),
    )
    blob = json.dumps(bundle.as_dict())
    assert secret not in blob
    assert "password=***" in blob
    assert bundle.provenance["dsn"] == "postgresql://ccf:***@192.168.4.76/ccf_v2"


def test_the_junit_rendering_is_well_formed_and_carries_the_exact_node_id(tmp_path: Path) -> None:
    """The ``file`` attribute is written explicitly — what ``junit_family=xunit1``
    preserves and ``xunit2`` drops — and the exact node id goes to ``name``, so
    nothing has to be reconstructed from a dotted ``classname``."""
    bundle = build(
        provenance={"exit_status": 1},
        estate_before={}, estate_after={},
        collected=("tests/examples/test_cp_04.py::test_it[a::b]",),
        phase_reports={
            "tests/examples/test_cp_04.py::test_it[a::b]": (
                PhaseReport("call", "failed", 'boom "quoted" <angled> &amped'),
            )
        },
        collection_errors=(),
    )
    target = tmp_path / "out.xml"
    write_junit_xml(bundle, target)
    root = ET.fromstring(target.read_bytes())          # raises if malformed
    case = root.find("testcase")
    assert case is not None
    assert case.get("file") == "tests/examples/test_cp_04.py"
    assert case.get("name") == "test_it[a::b]"
    assert case.find("failure") is not None


def test_a_json_bundle_round_trips_through_write_and_read(tmp_path: Path) -> None:
    bundle = build(
        provenance={"exit_status": 0}, estate_before={}, estate_after={},
        collected=("t.py::a",),
        phase_reports={"t.py::a": (PhaseReport("call", "passed"),)},
        collection_errors=(),
    )
    target = tmp_path / "b.json"
    write_json(bundle, target)
    loaded = read_json(target)
    assert loaded is not None
    assert loaded["kind"] == BUNDLE_KIND
    assert loaded["version"] == BUNDLE_VERSION
    assert loaded["outcomes"]["t.py::a"]["outcome"] == "passed"


@pytest.mark.parametrize(
    "label,write,expected_fragment",
    [
        ("absent", None, "no such file"),
        ("not-json", "not json at all {{{", "not valid JSON"),
        ("json-list", "[1, 2, 3]", "not an object"),
    ],
)
def test_an_unreadable_bundle_reports_the_specific_reason_not_a_generic_one(
    tmp_path: Path, label: str, write: str | None, expected_fragment: str
) -> None:
    """A file that does not exist and a file that is damaged are different problems
    with different fixes. Collapsing them gives the right exit code with the wrong
    diagnosis, which this project sent a measurement tool back for twice."""
    target = tmp_path / "b.json"
    if write is not None:
        target.write_text(write)
    loaded, reason = read_json_with_reason(target)
    assert loaded is None, label
    assert reason is not None and expected_fragment in reason, f"{label}: {reason!r}"


def test_a_directory_in_place_of_a_bundle_is_refused_rather_than_read(tmp_path: Path) -> None:
    loaded, reason = read_json_with_reason(tmp_path)
    assert loaded is None
    assert reason == "not a regular file"


def test_credential_in_file_finds_a_secret_written_by_a_path_this_module_does_not_own(
    tmp_path: Path,
) -> None:
    """The bytes are read, not the parsed object, so a secret that reached the file
    some other way is still caught."""
    target = tmp_path / "raw.xml"
    target.write_text('<failure message="host=h user=u password=NOTREDACTED dbname=d"/>')
    assert credential_in_file(target) is not None
    clean = tmp_path / "clean.xml"
    clean.write_text('<failure message="host=h user=u password=*** dbname=d"/>')
    assert credential_in_file(clean) is None


def test_credential_in_file_on_a_missing_path_is_none_and_not_an_exception(tmp_path: Path) -> None:
    assert credential_in_file(tmp_path / "nope.json") is None
