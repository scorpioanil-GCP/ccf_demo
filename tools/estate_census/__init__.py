"""In-tree estate census instrument — proof and support machinery.

`D-IMPL-358` ruling 8, under the `D-IMPL-276` proof-infrastructure charter.
**Support machinery, not production mechanism**: nothing here is part of the
SDK's public surface, nothing in `src/` or `runtime/` imports it, and it ships no
capability an adopter consumes.

Dave's standing correction to Wave 1, which is why this lives in the repository
at all: *"This time the qualification method must be reviewable from the
repository."* Wave 1's equivalents were preserved on a record branch rather than
in the SDK tree, so the method that qualified a release could not be read beside
the code it qualified.

What the instrument does, in the order a census runs it:

1. `tools/estate_census/watermarks.py::measure` — read the declared curated
   stores' positions, read-only, before the run.
2. `tools/estate_census/reporter.py::CensusReporter` — a pytest plugin that
   captures exact node ids and per-phase outcomes and writes them **already
   redacted**.
3. `tools/estate_census/watermarks.py::measure` again, after the run.
4. `tools/estate_census/classify.py::classify` — one verdict: PASS, HOLD, or
   INDETERMINATE, over exact node-id sets and mechanically-compared estate
   positions.

`tools/estate_census/redaction.py` is used by every step, because a credential
must never enter an artifact in the first place rather than be removed from one.
"""

from __future__ import annotations

from tools.estate_census.classify import HOLD, INDETERMINATE, PASS, Verdict, classify
from tools.estate_census.evidence import (
    EvidenceBundle,
    build,
    read_json,
    redact_structure,
    write_json,
)
from tools.estate_census.redaction import find_credential, redact_target, redact_text
from tools.estate_census.watermarks import load_roster, measure

__all__ = [
    "EvidenceBundle",
    "HOLD",
    "INDETERMINATE",
    "PASS",
    "Verdict",
    "build",
    "classify",
    "find_credential",
    "load_roster",
    "measure",
    "read_json",
    "redact_structure",
    "redact_target",
    "redact_text",
    "write_json",
]
