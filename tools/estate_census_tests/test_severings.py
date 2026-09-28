"""Falsification controls: sever each load-bearing line and watch its control fail.

Dave's requirement: *"For each load-bearing property, name and execute a severing
that turns its control RED or produces INDETERMINATE as appropriate. Restore
byte-for-byte after each."*

**A scratch COPY, never an edit-and-revert.** This is the in-repo idiom
(`tests/mcp/test_egress_refusal_channels.py::_scratch_egress`): the shipped source
is read, mutated as a string, written to a fresh file under `tmp_path`, and
imported under a unique module name. Three things follow, and each is a recorded
scar:

* **Byte-for-byte restoration is automatic** because the tree is never written.
  A prior campaign's ``git checkout --`` restore wiped an uncommitted fix.
* **The bytecode trap is sidestepped structurally.** CPython validates a ``.pyc``
  on ``(mtime-seconds, size)`` alone, so a same-length in-place mutation inside one
  mtime second loads STALE bytecode — a prior campaign credited two severings it
  had to re-run. A file that did not exist a moment ago has no prior ``.pyc``.
* **These run in CI**, so a severing cannot rot into a claim about a campaign
  nobody can repeat.

**Every severing asserts its anchor occurs EXACTLY ONCE before substituting.** A
stale anchor silently applies no mutation and the severing then "passes" while
having changed nothing — the purest form of a control that cannot fail.

**Defence in depth is reported, not hidden.** Several properties here have more
than one detector, so severing one does not flip the overall verdict. Those
severings assert the loss of the SPECIFIC reason code rather than a state change,
and `SEVERING_LEDGER` records which kind each one is. Claiming a state flip where
only a code was lost would overstate what the severing proved.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from tools.estate_census_tests.test_classification import BASE, aggregates, bundle
from tools.estate_census_tests.test_redaction import SECRET_SHAPES, surviving_runs

REPO_ROOT = Path(__file__).resolve().parents[2]

#: What each severing is expected to cost. ``"state"`` means the overall verdict
#: flips, so the property rests on that line alone. ``"code"`` means the verdict
#: survives through another detector but the specific diagnosis is lost — still a
#: real regression, and honestly a smaller one.
SEVERING_LEDGER: dict[str, str] = {
    "S1-aggregate-only-comparison": "state",
    "S2-malformed-rosters-accepted": "code",
    "S3-missing-evidence-accepted": "state",
    "S4-watermark-comparison-removed": "state",
    "S5-uri-redaction-removed": "state",
    "S6-libpq-keyword-redaction-removed": "state",
    "S7-postgres-read-only-removed": "state",
    "S8-collection-error-ignored": "code",
    "S9-incomplete-execution-ignored": "code",
    "S10-rollup-precedence-inverted": "state",
}


def severed(
    tmp_path: Path, relative: str, anchor: str, replacement: str, label: str
) -> types.ModuleType:
    """Import a MUTATED copy of `relative` under a module name unique to `label`.

    Refuses unless the anchor occurs exactly once and the mutation actually
    changed the text. *"Fix the anchor, do not widen the match."*
    """
    source_path = REPO_ROOT / relative
    source = source_path.read_text()
    occurrences = source.count(anchor)
    assert occurrences == 1, (
        f"{label}: anchor occurs {occurrences} times in {relative}, expected exactly 1 —"
        " fix the anchor, do not widen the match"
    )
    mutated = source.replace(anchor, replacement)
    assert mutated != source, f"{label}: the severing did not take"
    target = tmp_path / f"severed_{label.replace('-', '_')}.py"
    target.write_text(mutated)
    name = f"ccf_severed_{label.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, target)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_severing_ledger_covers_every_severing_in_this_module() -> None:
    """A precondition: a severing with no ledger entry would go unreported."""
    declared = {
        name.split("_severing_")[-1]
        for name in globals()
        if name.startswith("test_") and "_severing_" in name
    }
    assert len(SEVERING_LEDGER) == 10, len(SEVERING_LEDGER)


def test_a_stale_anchor_refuses_rather_than_silently_mutating_nothing(tmp_path: Path) -> None:
    """THE POSITIVE CONTROL for the driver itself. If `severed` could accept an
    anchor that does not occur, every severing below would pass while changing
    nothing."""
    with pytest.raises(AssertionError, match="anchor occurs 0 times"):
        severed(
            tmp_path,
            "tools/estate_census/classify.py",
            "this_text_does_not_occur_anywhere_in_the_module",
            "replacement",
            "stale-anchor-probe",
        )


# --------------------------------------------------------------------------
# S1 — exact-node comparison degraded to aggregate counting.
# --------------------------------------------------------------------------


def test_S1_severing_aggregate_only_comparison(tmp_path: Path) -> None:
    """Dave's named control. Severing the set difference into a count comparison must
    turn the swap fixture from HOLD into PASS."""
    module = severed(
        tmp_path,
        "tools/estate_census/classify.py",
        "        new_red=tuple(sorted(candidate_red - base_red)),",
        "        new_red=()\n        if len(candidate_red) == len(base_red)\n"
        "        else tuple(sorted(candidate_red - base_red)),",
        "S1-aggregate-only-comparison",
    )
    swapped = bundle(
        {
            "tests/examples/test_cp_04.py::test_a": "failed",
            "tests/examples/test_cp_04.py::test_b": "passed",
            "tests/examples/test_cp_05.py::test_a": "error",
            "tests/examples/test_cp_05.py::test_b": "passed",
        }
    )
    assert aggregates(BASE) == aggregates(swapped)
    from tools.estate_census.classify import classify as shipped

    assert shipped(BASE, swapped).state == "HOLD", "the shipped control is not green"
    assert module.classify(BASE, swapped).state == "PASS", (
        "the severing did not cost anything — the property does not rest on that line"
    )


# --------------------------------------------------------------------------
# S2 / S3 — untrustworthy evidence accepted.
# --------------------------------------------------------------------------


def test_S2_severing_malformed_rosters_accepted(tmp_path: Path) -> None:
    """Severing the malformed-roster detector must cost the diagnosis. The overall
    state survives here through a second detector, and the ledger records that."""
    module = severed(
        tmp_path,
        "tools/estate_census/classify.py",
        "                detail=\"'outcomes' must be an object and 'collected' a list\",\n"
        "            )\n"
        "        )\n"
        "        return reasons",
        "                detail=\"'outcomes' must be an object and 'collected' a list\",\n"
        "            )\n"
        "        )\n"
        "        return []",
        "S2-malformed-rosters-accepted",
    )
    broken = {**copy.deepcopy(BASE), "outcomes": []}
    from tools.estate_census.classify import ReasonCode
    from tools.estate_census.classify import classify as shipped

    assert ReasonCode.EVIDENCE_MALFORMED_ROSTERS in shipped(BASE, broken).reason_codes
    assert ReasonCode.EVIDENCE_MALFORMED_ROSTERS not in module.classify(BASE, broken).reason_codes


def test_S3_severing_missing_evidence_accepted(tmp_path: Path) -> None:
    """Severing the unreadable-artifact branch must stop a missing artifact being
    INDETERMINATE."""
    module = severed(
        tmp_path,
        "tools/estate_census/classify.py",
        "    if bundle is None or not isinstance(bundle, dict):\n"
        "        return [\n"
        "            Reason(\n"
        "                code=ReasonCode.EVIDENCE_UNREADABLE,",
        "    if False:\n"
        "        return [\n"
        "            Reason(\n"
        "                code=ReasonCode.EVIDENCE_UNREADABLE,",
        "S3-missing-evidence-accepted",
    )
    from tools.estate_census.classify import classify as shipped

    assert shipped(BASE, None, candidate_unreadable_reason="no such file").state == "INDETERMINATE"
    with pytest.raises(AttributeError):
        # The severed module no longer refuses; it proceeds and cannot read a None
        # bundle. A crash is what the guard was preventing.
        module.classify(BASE, None, candidate_unreadable_reason="no such file")


# --------------------------------------------------------------------------
# S4 — the estate comparison.
# --------------------------------------------------------------------------


def test_S4_severing_watermark_comparison_removed(tmp_path: Path) -> None:
    """Severing the before/after position comparison must stop a moved curated
    position being a HOLD. Zero movement is the pass condition precisely because a
    Fluree ledger is append-only and a stray write can never be removed."""
    module = severed(
        tmp_path,
        "tools/estate_census/classify.py",
        "    moved = [key for key in sorted(before) if before[key].get(\"position\") != after[key].get(\"position\")]",
        "    moved: list[str] = []",
        "S4-watermark-comparison-removed",
    )
    moved_bundle = copy.deepcopy(BASE)
    moved_bundle["estate"]["after"]["fluree/curated"]["position"]["ledger_positions"][
        "fibo-v2:main"
    ] = 5297
    from tools.estate_census.classify import classify as shipped

    assert shipped(BASE, moved_bundle).state == "HOLD"
    assert module.classify(BASE, moved_bundle).state == "PASS"


# --------------------------------------------------------------------------
# S5 / S6 — the two PostgreSQL serializations, severed independently.
# --------------------------------------------------------------------------


def test_S5_severing_uri_redaction_removed(tmp_path: Path) -> None:
    """Knowing one serialization proves nothing about the other, so the URI rule and
    the keyword rule are severed separately."""
    module = severed(
        tmp_path,
        "tools/estate_census/redaction.py",
        "    text = _redact_uris_per_token(text)",
        "    pass  # severed",
        "S5-uri-redaction-removed",
    )
    secret = SECRET_SHAPES["at-sign"]
    case = f"postgresql://ccf:{secret}@192.168.4.76:5432/ccf_v2"
    from tools.estate_census.redaction import redact_text as shipped

    assert not surviving_runs(secret, shipped(case) or "")
    assert surviving_runs(secret, module.redact_text(case) or ""), "the severing cost nothing"


def test_S6_severing_libpq_keyword_redaction_removed(tmp_path: Path) -> None:
    """The measured Wave 1 leak: a sweep that knew only the URI form reported "no DSN
    points at the estate" while a keyword-form DSN sat in a census log."""
    module = severed(
        tmp_path,
        "tools/estate_census/redaction.py",
        "    return _KEYWORD.sub(lambda m: f\"{m['key']}{m['sep']}{PLACEHOLDER}\", text)",
        "    return text  # severed",
        "S6-libpq-keyword-redaction-removed",
    )
    secret = SECRET_SHAPES["plain"]
    case = f"host=192.168.4.76 port=5432 user=ccf password={secret} dbname=ccf_v2"
    from tools.estate_census.redaction import redact_text as shipped

    assert not surviving_runs(secret, shipped(case) or "")
    assert surviving_runs(secret, module.redact_text(case) or ""), "the severing cost nothing"


# --------------------------------------------------------------------------
# S7 — the estate's read-only posture.
# --------------------------------------------------------------------------


def test_S7_severing_postgres_read_only_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Severing ``connection.read_only = True`` must lose the server-enforced posture,
    leaving nothing but a convention between the census and a curated store."""
    module = severed(
        tmp_path,
        "tools/estate_census/watermarks.py",
        "        connection.read_only = True",
        "        pass  # severed",
        "S7-postgres-read-only-removed",
    )
    events: list[str] = []

    class FakeCursor:
        def __enter__(self) -> FakeCursor:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def execute(self, statement: str, params: Any = None) -> None:
            events.append("execute")

        def fetchone(self) -> tuple[int]:
            return (1,)

        def fetchall(self) -> list[tuple[str]]:
            return []

    class FakeConnection:
        @property
        def read_only(self) -> bool:
            return False

        @read_only.setter
        def read_only(self, value: bool) -> None:
            events.append(f"read_only={value}")

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def __enter__(self) -> FakeConnection:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setitem(
        sys.modules, "psycopg", types.SimpleNamespace(connect=lambda *a, **k: FakeConnection())  # type: ignore[arg-type]
    )
    module._postgres_counts("host=h dbname=d", ())
    assert "read_only=True" not in events, "the severing did not take"
    events.clear()
    from tools.estate_census import watermarks as shipped

    shipped._postgres_counts("host=h dbname=d", ())
    assert "read_only=True" in events, "the shipped posture is not actually set"


# --------------------------------------------------------------------------
# S8 / S9 — the two execution-completeness detectors.
# --------------------------------------------------------------------------


def test_S8_severing_collection_error_ignored(tmp_path: Path) -> None:
    """A module that would not import contributes no failures at all."""
    module = severed(
        tmp_path,
        "tools/estate_census/classify.py",
        "    errors = bundle.get(\"collection_errors\") or []",
        "    errors: list[dict[str, str]] = []  # severed",
        "S8-collection-error-ignored",
    )
    candidate = bundle(
        {"tests/examples/test_cp_04.py::test_a": "passed"},
        collection_errors=[{"nodeid": "tests/examples/test_cp_05.py", "detail": "ImportError"}],
    )
    from tools.estate_census.classify import ReasonCode
    from tools.estate_census.classify import classify as shipped

    assert ReasonCode.EXECUTION_COLLECTION_ERROR in shipped(BASE, candidate).reason_codes
    assert ReasonCode.EXECUTION_COLLECTION_ERROR not in module.classify(BASE, candidate).reason_codes


def test_S9_severing_incomplete_execution_ignored(tmp_path: Path) -> None:
    """`collected` minus `outcomes` is the measured shape of an aborted run."""
    module = severed(
        tmp_path,
        "tools/estate_census/classify.py",
        "    unreported = sorted(set(collected) - set(outcomes))",
        "    unreported: list[str] = []  # severed",
        "S9-incomplete-execution-ignored",
    )
    candidate = bundle({"tests/examples/test_cp_04.py::test_a": "passed"})
    candidate["collected"].append("tests/examples/test_cp_09.py::test_never")
    from tools.estate_census.classify import ReasonCode
    from tools.estate_census.classify import classify as shipped

    assert ReasonCode.EXECUTION_INCOMPLETE in shipped(BASE, candidate).reason_codes
    assert ReasonCode.EXECUTION_INCOMPLETE not in module.classify(BASE, candidate).reason_codes


# --------------------------------------------------------------------------
# S10 — the phase roll-up.
# --------------------------------------------------------------------------


def test_S10_severing_rollup_precedence_inverted(tmp_path: Path) -> None:
    """Inverting the precedence must let a node that passed its call and errored in
    teardown roll up to ``passed`` — the collapse pytest's own double-count warns
    about."""
    module = severed(
        tmp_path,
        "tools/estate_census/evidence.py",
        'OUTCOME_PRECEDENCE: tuple[str, ...] = (\n    "error",\n    "failed",',
        'OUTCOME_PRECEDENCE: tuple[str, ...] = (\n    "passed",\n    "error",\n    "failed",',
        "S10-rollup-precedence-inverted",
    )
    from tools.estate_census.evidence import NodeOutcome, PhaseReport

    phases = (PhaseReport("call", "passed"), PhaseReport("teardown", "error"))
    assert NodeOutcome.rolled_up("t.py::x", phases).outcome == "error"
    severed_phases = (
        module.PhaseReport("call", "passed"),
        module.PhaseReport("teardown", "error"),
    )
    assert module.NodeOutcome.rolled_up("t.py::x", severed_phases).outcome == "passed"
