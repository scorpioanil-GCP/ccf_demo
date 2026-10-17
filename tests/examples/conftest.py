# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Two safety corrections for every example test (Dave, 2026-10-16 18:35, ruling 3).

*"These are pure safety corrections. ... Do not otherwise alter the frozen
examples."* Both live here, in the directory's shared configuration, so that no
frozen example's test file changes (`D-IMPL-261`).

**1 · A failed estate connection never prints the database password.** When a
connection fails, pytest renders the arguments of the frame that raised, and
psycopg's connect frame holds the whole connection string. Measured 2026-10-16
with every estate variable pointed at a closed loopback port and a marker
password: 28 example test modules printed the marker
(``test_example_test_output_safety.py`` holds the correction on one of them,
with a control). Every report — the failure text and the captured output — is
checked for password-shaped text (a ``password=`` or ``PGPASSWORD=`` value, the
password in a ``scheme://user:password@`` URL) and that text is withheld before
pytest shows it. It goes by the SHAPE, never by a password's value: a value
sweep for a weak secret rewrites unrelated text.

**2 · A collateral service a test starts never writes into the operator's
evidence folder.** cp-06-canonical's door keeps every decision under
``CCF_REPLAY_EVIDENCE_ROOT`` when that is set (`D-IMPL-383`), and an operator's
shell sets it for their own runs, so a door a test started inherited it and wrote
there (measured: four modules). It is removed for the whole test session; a test
that needs it sets it itself.
"""

from __future__ import annotations

import re
from collections.abc import Generator, Iterator
from typing import Any

import pytest

#: cp-06-canonical's ``server/serve.py::EVIDENCE_ROOT_VARIABLE``, restated;
#: ``tests/examples/test_example_test_output_safety.py`` holds the two equal.
EVIDENCE_ROOT_VARIABLE = "CCF_REPLAY_EVIDENCE_ROOT"

WITHHELD = "<withheld>"

#: Password-shaped text, by context: (what precedes the value, the value, what
#: follows it). Each match is bounded to one token, so a match can never run on
#: into the surrounding text.
_PASSWORD_SHAPES: tuple[re.Pattern[str], ...] = (
    # postgresql://user:secret@host, mongodb://user:secret@host -> user:<withheld>@
    re.compile(r"(\b[a-z][a-z0-9+.\-]*://[^:/@\s'\"]+:)([^@\s'\"]+)(@)", re.I),
    # password=secret, password = 'secret', 'password': 'secret', PGPASSWORD=secret
    re.compile(
        r"(\b(?:pg)?password['\"]?\s*[=:]\s*)('(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|[^\s'\",)]+)()",
        re.I,
    ),
)

#: Values that are not a password and stay as they are: a mask another guard
#: already wrote (``***``, ``<redacted>``, this file's own ``<withheld>``), and a
#: placeholder in source code a traceback shows (``{secret}``, ``{password!r}``).
_NOT_A_PASSWORD = re.compile(r"\*+|<[a-z]+>|\{[A-Za-z_][\w.]*(?:![rsa])?\}?")


def _withhold(match: re.Match[str]) -> str:
    before, value, after = match.groups()
    if _NOT_A_PASSWORD.fullmatch(value.strip("'\"")):
        return match.group(0)
    return f"{before}{WITHHELD}{after}"


def withhold_credentials(text: str) -> str:
    """``text`` with every password-shaped value replaced by ``<withheld>``."""
    for pattern in _PASSWORD_SHAPES:
        text = pattern.sub(_withhold, text)
    return text


def _withhold_in_report(report: pytest.TestReport | pytest.CollectReport) -> None:
    longrepr: Any = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:  # a skip: (path, line, reason)
        path, line, reason = longrepr
        report.longrepr = (path, line, withhold_credentials(str(reason)))
    elif longrepr is not None:
        rendered = report.longreprtext
        withheld = withhold_credentials(rendered)
        if withheld != rendered:
            # The rendered text replaces the structured report only when it carried
            # a credential; every other report keeps pytest's own rendering.
            report.longrepr = withheld
    report.sections = [(title, withhold_credentials(content)) for title, content in report.sections]


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    _withhold_in_report(report)
    return report


@pytest.hookimpl(wrapper=True)
def pytest_make_collect_report(collector: pytest.Collector) -> Generator[None, pytest.CollectReport, pytest.CollectReport]:
    report = yield
    _withhold_in_report(report)
    return report


@pytest.fixture(scope="session", autouse=True)
def _no_inherited_evidence_root() -> Iterator[None]:
    """No door a test starts inherits the operator's evidence folder (ruling 3, second half)."""
    with pytest.MonkeyPatch.context() as patch:
        patch.delenv(EVIDENCE_ROOT_VARIABLE, raising=False)
        yield
