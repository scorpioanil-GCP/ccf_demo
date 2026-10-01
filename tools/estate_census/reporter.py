"""The pytest plugin that captures census evidence, redacted at generation time.

`D-IMPL-358` ruling 8. Loaded with ``-p tools.estate_census.reporter`` and
configured entirely from the environment, so no census-specific option has to be
threaded through a Makefile target.

**Inert unless asked.** With `OUT_JSON_ENV` unset the plugin registers nothing
and the run is byte-identical to one without it. That matters because this module
sits in a tree ordinary suites import from, and a reporter that wrote a file on
every run would eventually write one nobody asked for.
`tools/estate_census_tests/test_reporter.py::test_the_reporter_is_inert_when_no_output_path_is_declared`
pins it.

**Why a plugin and not ``--junitxml``.** Measured: ``--junitxml`` writes
assertion text verbatim, so a credential in a traceback reaches disk before
anything can redact it — which makes every later sweep post-generation
scanning, admitted as defense in depth and explicitly refused as the primary
protection. Here every string goes through
`tools/estate_census/evidence.py::build`, which redacts on the way in.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from tools.estate_census.evidence import (
    PhaseReport,
    build,
    census_outcome,
    write_json,
    write_junit_xml,
)

#: Where the primary JSON bundle is written. Absent means the plugin is inert.
OUT_JSON_ENV = "CCF_CENSUS_OUT_JSON"

#: Optional JUnit rendering, for tooling that speaks JUnit. Interoperability
#: only — the JSON bundle is what the classifier trusts.
OUT_XML_ENV = "CCF_CENSUS_OUT_XML"

#: Optional path to the before-run estate measurement, embedded in the bundle so
#: one file carries the whole run. `tools/estate_census/__main__.py` writes it.
ESTATE_BEFORE_ENV = "CCF_CENSUS_ESTATE_BEFORE"

#: A free-text label for the run (a chunk name, say), recorded in provenance.
LABEL_ENV = "CCF_CENSUS_LABEL"


def _git(root: Path, *args: str) -> str:
    """A git value, or the empty string. A census must not fail on git."""
    try:
        done = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


class CensusReporter:
    """Collects phase reports and collection errors, then writes the bundle."""

    def __init__(self, out_json: Path, out_xml: Path | None, estate_before: dict[str, Any], label: str) -> None:
        self._out_json = out_json
        self._out_xml = out_xml
        self._estate_before = estate_before
        self._label = label
        self._collected: list[str] = []
        self._phases: dict[str, list[PhaseReport]] = defaultdict(list)
        self._collection_errors: list[dict[str, str]] = []

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        """The roster pytest SELECTED, kept apart from what reported.

        Deselected nodes never appear here, which is correct and is why the
        classifier compares this against the outcomes: the gap between selected
        and reported is the measured shape of an aborted run.
        """
        self._collected = [item.nodeid for item in items]

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        outcome = census_outcome(report.when or "", report.outcome, hasattr(report, "wasxfail"))
        if outcome is None:
            return
        self._phases[report.nodeid].append(
            PhaseReport(
                when=report.when or "",
                outcome=outcome,
                detail=self._detail(report),
            )
        )

    @staticmethod
    def _detail(report: pytest.TestReport) -> str:
        """The failure text plus captured sections, unredacted HERE by design.

        Redaction is `tools/estate_census/evidence.py::build`'s job and happens
        before anything is serialized. Doing it twice would invite the two copies
        to drift; doing it here and not there would leave `build` trusting its
        caller. The captured ``sections`` are included because a credential
        printed to stdout by a failing test is in them and not in the traceback.
        """
        parts = [report.longreprtext or ""]
        parts.extend(text for _title, text in getattr(report, "sections", ()) if text)
        return "\n".join(part for part in parts if part)[:8000]

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        """A module that would not import.

        Recorded because it is invisible everywhere else: measured, one
        uncollectable module makes pytest exit 2 having run **nothing**, while a
        summary counting only failures shows none.
        """
        if report.outcome == "failed":
            self._collection_errors.append(
                {"nodeid": report.nodeid, "detail": (report.longreprtext or "")[:8000]}
            )

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        root = Path(str(session.config.rootpath))
        bundle = build(
            provenance={
                "label": self._label,
                "exit_status": int(exitstatus),
                "commit": _git(root, "rev-parse", "HEAD"),
                "tree": _git(root, "rev-parse", "HEAD^{tree}"),
                "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
                "dirty": bool(_git(root, "status", "--porcelain")),
                "rootpath": str(root),
                "pytest_version": pytest.__version__,
                "python_version": platform.python_version(),
                "invocation_args": list(session.config.invocation_params.args),
            },
            estate_before=self._estate_before,
            estate_after={},
            collected=tuple(self._collected),
            phase_reports={node: tuple(phases) for node, phases in self._phases.items()},
            collection_errors=tuple(self._collection_errors),
        )
        write_json(bundle, self._out_json)
        if self._out_xml is not None:
            write_junit_xml(bundle, self._out_xml)


def pytest_configure(config: pytest.Config) -> None:
    """Register the reporter only when an output path is declared."""
    out_json = os.environ.get(OUT_JSON_ENV)
    if not out_json:
        return
    before_path = os.environ.get(ESTATE_BEFORE_ENV)
    estate_before: dict[str, Any] = {}
    if before_path:
        try:
            loaded = json.loads(Path(before_path).read_text())
            if isinstance(loaded, dict):
                estate_before = loaded
        except (OSError, ValueError):
            # An unreadable before-measurement leaves the field EMPTY rather than
            # inventing one. The classifier refuses a bundle with no measured
            # before position, so the failure surfaces as INDETERMINATE instead
            # of as a run that silently proved nothing about the estate.
            estate_before = {}
    out_xml = os.environ.get(OUT_XML_ENV)
    config.pluginmanager.register(
        CensusReporter(
            out_json=Path(out_json),
            out_xml=Path(out_xml) if out_xml else None,
            estate_before=estate_before,
            label=os.environ.get(LABEL_ENV, ""),
        ),
        "ccf-estate-census-reporter",
    )
