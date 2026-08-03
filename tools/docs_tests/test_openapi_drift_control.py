"""Standing negative control for the D-12 OpenAPI drift check (14-03).

The other three drift classes in the documentation suite — the snippet
marker, the mkdocstrings identifier, and the publish scan — each land as a
committed executable test that exercises the *failing* polarity on every
run. Without this file the OpenAPI drift class would be the only one whose
failure polarity was proven once, by a reverted acceptance probe, with
nothing standing to show the comparison still discriminates after a future
refactor of the serialization helper. A gate that has silently stopped
firing looks exactly like a gate that has nothing to complain about.

So: mutate a copy of the committed spec **in memory**, and assert the
comparison reports a difference. The companion clean case asserts the
unmutated copy still compares equal, so a comparison that reports a
difference for *everything* fails here too.

This lives in `tools/docs_tests/` rather than `tests/` for the reason
`tools/lints/tests/` states: a gate's own controls sit outside `testpaths`
and run in the CI step that precedes the gate they defend. Plan 14-10's CI
job already runs `pytest tools/publish_scan_tests tools/docs_tests -q`, so
this file joins that step with no further wiring.

Two disciplines this file keeps:

- **It never writes.** Not to `openapi.json`, not anywhere. The mutation is
  on a parsed copy held in memory.
- **It hard-codes no endpoint name.** The path it renames is whichever key
  sorts first, so adding, removing or renaming routes cannot make the
  control quietly stop testing anything.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from tools.dump_openapi import OPENAPI_PATH, serialize


def _committed_text() -> str:
    return OPENAPI_PATH.read_text(encoding="utf-8")


def _committed_document() -> dict[str, Any]:
    document: dict[str, Any] = json.loads(_committed_text())
    return document


def test_an_unmutated_copy_compares_equal() -> None:
    """The clean pole: the comparison is not simply always unhappy."""
    assert serialize(_committed_document()) == _committed_text()


def test_a_renamed_endpoint_is_reported_as_a_difference() -> None:
    """The failing pole, exercised on every run — the point of this file."""
    mutated = copy.deepcopy(_committed_document())
    paths = mutated["paths"]
    assert paths, "the committed spec advertises no endpoints to mutate"

    # Whichever path sorts first — never a literal endpoint name, so route
    # churn cannot turn this control into a no-op.
    victim = sorted(paths)[0]
    paths[victim + "-drift-control"] = paths.pop(victim)

    assert serialize(mutated) != _committed_text()


def test_a_changed_description_is_reported_as_a_difference() -> None:
    """A subtler mutation: prose drift inside the document, not its shape."""
    mutated = copy.deepcopy(_committed_document())
    mutated["info"]["description"] += " (drift control sentinel)"

    assert serialize(mutated) != _committed_text()
