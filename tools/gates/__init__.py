"""Phase-local gates — checks that assert a fact about ONE phase's diff.

Deliberately **not** `tools/lints`. A lint in `tools/lints` is a standing
invariant: it is expected to hold for every commit forever, and it grows rules
over time. A gate in here is the opposite kind of object — it asserts something
about a particular phase's change surface, it is only meaningful against that
phase's base ref, and it is expected to be **superseded** by the next phase's
gate rather than extended into a permanent rule (Phase 15.3 CONTEXT.md D-10).

Gates copy `tools/lints`' *output contract* — findings as
``path:line rule message`` on stdout, a summary on stderr, nonzero exit on any
finding, no report-only mode (D-07) — and nothing else about it.
"""

from __future__ import annotations

__all__: list[str] = []
