"""The census evidence bundle: what a run measured, redacted, and replayable.

`D-IMPL-358` ruling 8, support machinery under `D-IMPL-276`.

**Why the census writes its own artifact instead of asking pytest for one.**
Three measured reasons, each independently sufficient:

* **Generation-time redaction is only possible here.** ``--junitxml`` writes
  assertion text verbatim — measured, a synthetic secret appeared six times in
  the emitted file. Anything done afterwards is post-generation scanning, which
  Dave's contract admits as defense in depth and explicitly refuses as the
  primary protection. A bundle this module builds has every string through
  `tools/estate_census/redaction.py::redact_text` *before* it is serialized.
* **JUnit XML cannot represent a pytest node id unambiguously.** Its
  ``classname`` is a dotted module path, so the runnable id has to be
  reconstructed — and a parametrized id may itself contain ``::``
  (``test_p[c::d]``), which is indistinguishable from a class separator. Wave 1's
  classification evidence is in the dotted, non-runnable form for this reason.
  `pytest_runtest_logreport` hands over ``report.nodeid`` exactly.
* **One node id can own more than one outcome.** Measured: a node that passes
  its call and raises in teardown is counted by pytest as *both* a pass and an
  error. A mapping of node id to a single outcome loses that, so `NodeOutcome`
  keeps the phase reports and derives a roll-up with a stated precedence.

**The four numbers are four numbers.** ``passed``, ``failed``, ``errors`` and
``skipped`` are counted independently from the phase reports and never derived
from each other or from an exit code. `Counts` additionally keeps ``xfailed``
and ``xpassed`` out of all four, because an expected failure is this
repository's in-code known-red ledger (`D-IMPL-261` permits quarantining a known
gap as an expected failure) and burying it in ``passed`` or ``skipped`` would
hide the evidence the census exists to surface.
"""

from __future__ import annotations

import dataclasses
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from tools.estate_census.redaction import find_credential, redact_text

#: Bundle discriminator. A file that does not carry it is not census evidence,
#: whatever else it parses as.
BUNDLE_KIND = "ccf-estate-census-evidence"

#: Schema version. An unknown version is INDETERMINATE, never best-effort: a
#: classifier guessing at an older shape is how a field that changed meaning
#: gets read with its old meaning.
BUNDLE_VERSION = 1

#: Roll-up precedence, most severe first. A node with reports in several phases
#: takes the most severe. ``error`` outranks ``failed`` because a fixture that
#: raised means the assertion never ran, which is a different and larger fact.
OUTCOME_PRECEDENCE: tuple[str, ...] = (
    "error",
    "failed",
    "xpassed",
    "xfailed",
    "skipped",
    "passed",
)

#: The outcomes that count as RED for classification. Deliberately narrow:
#: ``xfailed`` is a DECLARED known red and is reported in its own category, and
#: ``xpassed`` is a stale marker rather than a failure. Widening this set would
#: turn every quarantined known gap into a new red on the first census.
RED_OUTCOMES: frozenset[str] = frozenset({"failed", "error"})


def census_outcome(when: str, pytest_outcome: str, was_xfail: bool) -> str | None:
    """Translate one pytest phase report into the census vocabulary.

    **The single authority for this table, because the table is not obvious.**
    Every row below was measured against pytest 9.1.1 rather than reasoned
    about, and three rows contradict the natural reading:

    * A **declared skip emits no ``call`` report at all** — only
      ``setup/skipped`` then ``teardown/passed``. Code that keys on
      ``when == "call"`` silently loses every ``@pytest.mark.skip`` node.
    * A **teardown failure is an ERROR, not a failure**, and it arrives on a
      node whose ``call`` already reported ``passed`` — which is why pytest's own
      summary counts such a node once as a pass and once as an error.
    * An **xfail reports ``skipped`` and an xpass reports ``passed``**, both
      distinguished only by ``report.wasxfail``; a **strict** xpass reports a
      plain ``failed`` and is correctly read as a failure.

    Returns ``None`` for a phase that carries no census meaning (a passing
    ``setup`` or ``teardown``), so the caller records nothing rather than
    recording a pass twice.
    """
    if was_xfail:
        if pytest_outcome == "skipped":
            return "xfailed"
        if pytest_outcome == "passed":
            return "xpassed"
    if when == "call":
        return pytest_outcome if pytest_outcome in ("passed", "failed", "skipped") else None
    if pytest_outcome == "failed":
        return "error"
    if when == "setup" and pytest_outcome == "skipped":
        return "skipped"
    return None


@dataclasses.dataclass(frozen=True)
class PhaseReport:
    """One `pytest_runtest_logreport` call, reduced to what a census needs.

    `outcome` is in the CENSUS vocabulary — the output of `census_outcome`, not
    pytest's raw ``report.outcome``. The distinction is load-bearing and easy to
    get wrong: ``PhaseReport(when="teardown", outcome="failed")`` reads as
    correct and is not, because a teardown failure is an ``error``. Constructing
    these through `census_outcome` is the supported path.
    """

    when: str
    outcome: str
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"when": self.when, "outcome": self.outcome, "detail": self.detail}


@dataclasses.dataclass(frozen=True)
class NodeOutcome:
    """Every phase report for one node id, plus the derived roll-up.

    `phases` is the evidence; `outcome` is a reading of it. Keeping both is what
    lets a reviewer see that a node passed its call and errored in teardown
    rather than only that it was "an error".
    """

    nodeid: str
    phases: tuple[PhaseReport, ...]
    outcome: str

    @staticmethod
    def rolled_up(nodeid: str, phases: tuple[PhaseReport, ...]) -> NodeOutcome:
        seen = {phase.outcome for phase in phases}
        for candidate in OUTCOME_PRECEDENCE:
            if candidate in seen:
                return NodeOutcome(nodeid=nodeid, phases=phases, outcome=candidate)
        return NodeOutcome(nodeid=nodeid, phases=phases, outcome="passed")

    @property
    def is_red(self) -> bool:
        return self.outcome in RED_OUTCOMES

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "phases": [phase.as_dict() for phase in self.phases],
        }


@dataclasses.dataclass(frozen=True)
class Counts:
    """Six independent tallies. None is derived from another or from an exit code."""

    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    xfailed: int = 0
    xpassed: int = 0

    @staticmethod
    def over(outcomes: dict[str, NodeOutcome]) -> Counts:
        tally = {key: 0 for key in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")}
        for node in outcomes.values():
            tally[node.outcome] = tally.get(node.outcome, 0) + 1
        return Counts(
            passed=tally["passed"],
            failed=tally["failed"],
            errors=tally["error"],
            skipped=tally["skipped"],
            xfailed=tally["xfailed"],
            xpassed=tally["xpassed"],
        )

    def as_dict(self) -> dict[str, int]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class EvidenceBundle:
    """One census capture. Immutable, redacted, and self-describing.

    `collected` is the roster pytest *selected*; `outcomes` is what actually
    reported. They are kept separately and compared by
    `tools/estate_census/classify.py::classify`, because the gap between them is
    the measured shape of an aborted run: a single uncollectable module makes
    pytest exit 2 having run **nothing**, while a summary that counts only
    failures shows none.
    """

    kind: str
    version: int
    provenance: dict[str, Any]
    estate_before: dict[str, Any]
    estate_after: dict[str, Any]
    collected: tuple[str, ...]
    outcomes: dict[str, NodeOutcome]
    collection_errors: tuple[dict[str, str], ...]
    counts: Counts

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "provenance": self.provenance,
            "estate": {"before": self.estate_before, "after": self.estate_after},
            "collected": list(self.collected),
            "outcomes": {node: value.as_dict() for node, value in sorted(self.outcomes.items())},
            "collection_errors": [dict(entry) for entry in self.collection_errors],
            "counts": self.counts.as_dict(),
        }

    @property
    def red_nodes(self) -> frozenset[str]:
        return frozenset(node for node, value in self.outcomes.items() if value.is_red)

    def with_estate(self, *, before: dict[str, Any], after: dict[str, Any]) -> EvidenceBundle:
        """The same bundle with estate positions attached.

        The reporter runs inside pytest and cannot measure the estate after the
        session it is part of, so the after-position is attached by
        `tools/estate_census/__main__.py` once the run has ended. Returning a new
        frozen bundle rather than mutating keeps the redaction boundary intact:
        estate positions are counts and hashes, carry no free text, and are the
        only fields that arrive after `build`.
        """
        return dataclasses.replace(self, estate_before=before, estate_after=after)


def build(
    *,
    provenance: dict[str, Any],
    estate_before: dict[str, Any],
    estate_after: dict[str, Any],
    collected: tuple[str, ...],
    phase_reports: dict[str, tuple[PhaseReport, ...]],
    collection_errors: tuple[dict[str, str], ...],
) -> EvidenceBundle:
    """Assemble a bundle, redacting every free-text field on the way in.

    Redaction happens HERE rather than at write time so that no code path can
    serialize an unredacted value: a bundle that exists is a bundle that was
    redacted. `tools/estate_census_tests/test_reporter.py` asserts it against a
    synthetic failure carrying a credential in each supported serialization.
    """
    redacted_phases = {
        node: tuple(
            PhaseReport(
                when=phase.when,
                outcome=phase.outcome,
                detail=redact_text(phase.detail) or "",
            )
            for phase in phases
        )
        for node, phases in phase_reports.items()
    }
    outcomes = {
        node: NodeOutcome.rolled_up(node, phases) for node, phases in redacted_phases.items()
    }
    return EvidenceBundle(
        kind=BUNDLE_KIND,
        version=BUNDLE_VERSION,
        provenance={key: _redact_any(value) for key, value in provenance.items()},
        estate_before=estate_before,
        estate_after=estate_after,
        collected=tuple(redact_text(node) or "" for node in collected),
        outcomes=outcomes,
        collection_errors=tuple(
            {key: redact_text(value) or "" for key, value in entry.items()}
            for entry in collection_errors
        ),
        counts=Counts.over(outcomes),
    )


def _redact_any(value: Any) -> Any:
    """Redact strings anywhere inside a nested provenance value."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {key: _redact_any(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_any(item) for item in value]
    return value


def write_json(bundle: EvidenceBundle, path: Path) -> None:
    """Write the primary artifact. Sorted and indented so a diff is readable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle.as_dict(), indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any] | None:
    """The bundle at `path`, or ``None`` when it cannot be read.

    ``None`` means *don't know* and the caller must not read it as an empty
    result — the posture `tools/check_product_gates.py` states as *"None means
    the collection failed and NOTHING can be decided."* A missing file and a
    damaged file are both ``None`` here and are distinguished by the caller,
    which reports which one it was.
    """
    try:
        loaded = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def read_json_with_reason(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """The bundle at `path`, or ``None`` plus the SPECIFIC reason it is unreadable.

    `read_json` collapses every failure into ``None``, which is correct for
    *don't know* but gives an operator the right exit code with the wrong
    diagnosis: a file that does not exist and a file that exists and is damaged
    are different problems with different fixes. This project sent a measurement
    tool back twice for exactly that conflation, so the reason is separated here
    and reported ahead of any consequence it causes.
    """
    if not path.exists():
        return None, "no such file"
    if not path.is_file():
        return None, "not a regular file"
    try:
        text = path.read_text()
    except OSError as exc:
        return None, f"unreadable: {type(exc).__name__}: {exc}"
    try:
        loaded = json.loads(text)
    except ValueError as exc:
        return None, f"exists but is not valid JSON: {exc}"
    if not isinstance(loaded, dict):
        return None, f"top-level JSON value is {type(loaded).__name__}, not an object"
    return loaded, None


def write_junit_xml(bundle: EvidenceBundle, path: Path) -> None:
    """A JUnit rendering of an ALREADY-REDACTED bundle, for ordinary tooling.

    Interoperability only — `write_json` is the artifact the classifier trusts,
    because JUnit cannot carry an unambiguous node id. The ``file`` attribute is
    written explicitly (what ``junit_family=xunit1`` preserves and ``xunit2``
    drops) and the exact node id is written to ``name``, so nothing here has to
    be reconstructed from a dotted ``classname``.

    **This is where per-field redaction earns itself.** Every value below was
    redacted when the bundle was built, and the XML writer adds the quoting and
    escaping afterwards — so a credential-bearing traceback containing a quote
    or an angle bracket cannot corrupt the document. Sweeping a serialized
    document instead would let a greedy value class eat a closing delimiter,
    which is the incident that silently broke a census file for hours.
    """
    counts = bundle.counts
    suite = ET.Element(
        "testsuite",
        {
            "name": "ccf-estate-census",
            "tests": str(len(bundle.outcomes)),
            "failures": str(counts.failed),
            "errors": str(counts.errors),
            "skipped": str(counts.skipped + counts.xfailed),
        },
    )
    for nodeid, node in sorted(bundle.outcomes.items()):
        file_part, _, rest = nodeid.partition("::")
        case = ET.SubElement(
            suite,
            "testcase",
            {"name": rest or nodeid, "classname": file_part, "file": file_part},
        )
        detail = "\n".join(phase.detail for phase in node.phases if phase.detail)
        if node.outcome == "failed":
            ET.SubElement(case, "failure", {"message": "failed"}).text = detail
        elif node.outcome == "error":
            ET.SubElement(case, "error", {"message": "error"}).text = detail
        elif node.outcome in ("skipped", "xfailed"):
            ET.SubElement(case, "skipped", {"type": node.outcome}).text = detail
        elif node.outcome == "xpassed":
            # No JUnit tag means "unexpectedly passed", so say so rather than
            # letting it render as an ordinary pass and vanish from every count.
            ET.SubElement(case, "system-out").text = "xpassed: stale xfail marker"
    for entry in bundle.collection_errors:
        case = ET.SubElement(
            suite,
            "testcase",
            {"name": "COLLECTION", "classname": entry.get("nodeid", ""), "file": entry.get("nodeid", "")},
        )
        ET.SubElement(case, "error", {"message": "collection failure"}).text = entry.get("detail", "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ET.tostring(suite, encoding="utf-8", xml_declaration=True))


def credential_in_file(path: Path) -> str | None:
    """A credential grammar still present in the bytes at `path`, or ``None``.

    Dave's rule, verbatim: *"Raw evidence containing a secret is never committed
    and is not treated as valid census evidence."* So this is consulted before
    an artifact is trusted, and a hit is an INDETERMINATE verdict rather than a
    warning. Reading the bytes is deliberate: it catches a secret that reached
    the file through a path this module does not own.
    """
    try:
        return find_credential(path.read_text(errors="replace"))
    except OSError:
        return None
