"""A test-owned copy of an example's deployment, declaring the run's one time anchor.

Dave, 2026-10-11 16:23 MST, ruling 1 (`docs/DECISIONS.md`, "Tuesday delivery —
RULED"): *"Use one consistent time anchor per run … For historical time-based
demonstrations, retain the dated scenario and use the existing, explicitly
labelled development-clock mechanism where appropriate. Keep an expired-question
case as a normal test that asserts the correct refusal."*

The mechanism is the deployment's own Control Plane declaration
`demonstration_serve_instant:` (`D-IMPL-378` C1,
`ccf.products.demonstration_clock`). Nothing a question carries can move it, so a
test that asks a dated scenario at an instant other than the one the example's
own `ccf_config.yaml` declares acts as a DEPLOYER: it writes a copy of that
config into a directory the test owns, with only the declared serve instant
changed, and boots that copy. Every other section — the half-life table, the
debt profile, the temporal boundary, the gates — is byte-for-byte the example's
own, so the governed values under test are the example's, never the test's.

The SDK still refuses the declaration outside its own development substrates
(SQLite graph, file-backed store), and still pins it into dimension 2 of every
record written under it; a copy changes neither.
"""

from __future__ import annotations

import pathlib
import re
from datetime import datetime, timedelta

#: How long after the question's instant the test deployment serves. Five
#: minutes, the hw1-companies-over-revenue precedent: inside every example's
#: one-hour `temporal_boundary` and inside the answer's lifetime.
SERVE_AFTER = timedelta(minutes=5)

_SECTION = re.compile(r"^demonstration_serve_instant:\n(?:[ \t]+.*\n?)*", re.MULTILINE)


def deployment_serving_at(
    config: pathlib.Path, *, serve_instant: datetime, directory: pathlib.Path
) -> pathlib.Path:
    """Write ``config`` into ``directory`` declaring ``serve_instant``; return the copy's path.

    An existing ``demonstration_serve_instant:`` section is replaced, never
    duplicated (the SDK refuses two declarations by name); one that is absent
    is appended. Nothing else in the document changes.
    """
    if serve_instant.tzinfo is None:
        raise ValueError("a serve instant is timezone-aware; a naive one is refused by the loader")
    text = _SECTION.sub("", config.read_text(encoding="utf-8")).rstrip("\n")
    text += (
        "\n\n# TEST-OWNED DEMONSTRATION CLOCK — the run's one time anchor\n"
        "# (tests/examples/demonstration_deployment.py).\n"
        "demonstration_serve_instant:\n"
        f'  serve_instant: "{serve_instant.isoformat()}"\n'
    )
    directory.mkdir(parents=True, exist_ok=True)
    copy = directory / config.name
    copy.write_text(text, encoding="utf-8")
    return copy


def deployment_on_the_real_clock(config: pathlib.Path, *, directory: pathlib.Path) -> pathlib.Path:
    """Write ``config`` into ``directory`` WITHOUT any declared serve instant.

    The deployment then serves on the real clock, which is what makes an old
    pinned question an EXPIRED question — the case ruling 1 keeps as an ordinary
    test asserting the correct refusal.
    """
    text = _SECTION.sub("", config.read_text(encoding="utf-8")).rstrip("\n") + "\n"
    directory.mkdir(parents=True, exist_ok=True)
    copy = directory / config.name
    copy.write_text(text, encoding="utf-8")
    return copy


def anchored_after(asked_at: datetime) -> datetime:
    """The serve instant a test deployment declares for a question asked at ``asked_at``."""
    return asked_at + SERVE_AFTER
