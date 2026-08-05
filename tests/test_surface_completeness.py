"""ROADMAP Success Criterion 6 — the surface record's completeness, proven.

Criterion 6 asks that *every* removed or reshaped public surface be recorded,
so Phase 16 documents the surface that exists rather than the one that was.
This module is that guarantee in executable form: it diffs the frozen
phase-start baseline against the live public surface at **fully-qualified-name
granularity** and cross-checks the result against the curated
``docs/SURFACE-CHANGES.md`` in **both directions**, with the entry's
``Change type`` required to agree with the direction of the diff.

The pair, and why neither half is sufficient
--------------------------------------------

``tests/test_surface_drift.py`` is the standing gate. Its own docstring states
its limitation plainly: it is **module-granular and direction-blind by
design**. Fragments accumulate and are read as a union, so once 15-05 names
``ccf.controlplane.artifacts``, later drift anywhere in that module is claimed
for the rest of the phase — including an export *removed* by a later plan, and
including a fragment that says ``added`` where the manifest shows ``removed``.
That is the right trade for a cheap tripwire that has to stay green across
fourteen parallel waves. It is the wrong trade for the phase-close record.

This module is the paired half that docstring points at. It is exact, it runs
once at phase close and thereafter, and **weakening either half without the
other is a regression.**

Why the entries are partitioned before anything is asserted
-----------------------------------------------------------

The manifest is derived from every module's ``__all__``, so it can only ever
contain **Python public-API names**. The curated log deliberately carries more
than that, because D-15 requires it to carry everything an adopter must act on:
the lint-scope change (15-04), the measurement tooling (15-03), the committed
JSON Schemas (15-12), and the artifact-*document*-format changes (15-09 and
15-13 through 15-20). Demanding a manifest diff line for a YAML document format
would make this test unsatisfiable; ignoring those entries entirely would turn
``Public surface`` into an escape hatch.

Both are avoided by partitioning once, up front, and asserting each partition
against the thing it can actually be checked against — assertion 2 for public
entries, assertion 4 for non-public ones. **Assertions 2 and 4 together close
the classification in both directions**, which is why ``Public surface`` is a
checked field rather than an annotation: a real public-API addition mislabelled
``false`` to duck assertion 3 fails assertion 2 instead, with a message that
names the misclassification rather than reporting a missing entry.

Why the live side is computed rather than read
----------------------------------------------

``build_surface()`` is called rather than reading the committed
``docs/surface/v0.2-surface.json``. The committed file's currency is the drift
gate's job; this test is about whether the *record* covers the *reality*, and
reading the committed file would let a stale manifest and a matching stale log
agree with each other while both diverged from the code.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
from typing import Any

from tools.assemble_surface_changes import parse_entries
from tools.dump_surface import build_surface, diff_surfaces

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: The immutable "before" side, written once by plan 15-01 and never again.
_FROZEN_BASELINE = _REPO_ROOT / "docs" / "surface" / "v0.2-surface-baseline.json"

#: SHA-256 of ``_FROZEN_BASELINE`` as plan 15-01 committed it. Pinned as a
#: constant rather than recomputed, because a value recomputed from the file
#: under test is the exact self-satisfying shape this phase found eight times.
_BASELINE_DIGEST = (
    "cef0d469db249947f8392331a50bc94bf92d46a4266e4945e2b59944dac043cc"
)

#: Change types exempt from needing a matching diff line — see assertion 3.
#: ``behavior`` is the only one, because a signature diff cannot see a change
#: like D-02's to ``load_artifact``.
_DIFF_EXEMPT_CHANGE_TYPES = frozenset({"behavior"})

#: Behavior entries that MUST be present. ``behavior`` is exempt from diff
#: agreement, so without a named required member the exemption would let D-02's
#: entry go missing and fail only a human read. Kept as an explicit list so
#: adding a future exempt entry is a deliberate edit rather than a silent
#: widening of the exemption.
_REQUIRED_BEHAVIOR_SURFACES = frozenset(
    {"ccf.controlplane.artifacts.load_artifact"}
)

_DIRECTIONS = ("added", "removed", "reshaped")


def _diff() -> dict[str, list[str]]:
    baseline: dict[str, Any] = json.loads(
        _FROZEN_BASELINE.read_text(encoding="utf-8")
    )
    return diff_surfaces(baseline, build_surface())


def _partitions() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """(public entries, non-public entries) — the partition, made once."""
    entries = parse_entries()
    public = [entry for entry in entries if entry["Public surface"]]
    non_public = [entry for entry in entries if not entry["Public surface"]]
    return public, non_public


# --- 1. Non-vacuity -------------------------------------------------------


def test_the_diff_and_the_log_are_both_non_vacuous() -> None:
    """A diff that quietly came back empty makes every other assertion here
    vacuously true, which is the quietest way this test stops being one.

    Both partitions are asserted non-empty as well: the phase provably
    produced public-API changes *and* artifact-format changes, so an empty
    partition means the parser or the classification broke, not that the phase
    had nothing to say.
    """
    difference = _diff()
    assert set().union(*(difference[key] for key in _DIRECTIONS)), (
        "the baseline and the live surface do not differ at all — either the"
        " frozen baseline was overwritten with the current surface, or"
        " build_surface() returned the baseline"
    )

    public, non_public = _partitions()
    assert public, "no Public surface: true entries — the parser or the log broke"
    assert non_public, (
        "no Public surface: false entries — the phase provably changed lint"
        " scope, tooling, schemas and artifact document formats"
    )


# --- 2. diff -> log, name granularity, direction agreement ----------------


def test_every_diff_line_has_a_matching_public_log_entry() -> None:
    """Every name the manifest moved is claimed, with the right direction.

    Three failure cases are distinguished in the message, because a mismatched
    direction and a misclassification must not read as a missing entry:

    * no entry at all — the change was never recorded;
    * an entry whose ``Change type`` disagrees with the diff direction;
    * an entry that exists but is classified ``Public surface: false`` — the
      classification is wrong, and this is the assertion that catches an
      executor ducking assertion 3 by relabelling.
    """
    difference = _diff()
    entries = parse_entries()
    failures: list[str] = []

    for direction in _DIRECTIONS:
        for name in difference[direction]:
            named = [entry for entry in entries if entry["Surface"] == name]
            public_named = [
                entry for entry in named if entry["Public surface"]
            ]
            if not named:
                failures.append(
                    f"{direction}: {name} — NO ENTRY. The manifest moved this"
                    " name and no docs/surface-changes/ fragment claims it."
                )
                continue
            if not public_named:
                failures.append(
                    f"{direction}: {name} — WRONG CLASSIFICATION. An entry"
                    " exists but carries `Public surface: false`; the name"
                    " appears in the generated manifest diff, so it is public"
                    " Python API. Set `Public surface: true`."
                )
                continue
            found = sorted({str(e["Change type"]) for e in public_named})
            if direction not in found:
                failures.append(
                    f"{direction}: {name} — WRONG CHANGE TYPE. Found"
                    f" {found}; the manifest shows `{direction}`."
                )

    assert not failures, "\n".join(failures)


# --- 3. log -> diff, the reverse direction, public entries only -----------


def test_every_public_log_entry_has_a_matching_diff_line() -> None:
    """A claim with no diff line is a claim that did not happen.

    ``behavior`` entries are exempt and, among public entries, only they are:
    that class exists precisely because a signature diff cannot see D-02's
    change. Any other public entry with no diff line is a defect, not a
    tolerance.
    """
    difference = _diff()
    failures: list[str] = []
    public, _ = _partitions()

    for entry in public:
        change_type = str(entry["Change type"])
        if change_type in _DIFF_EXEMPT_CHANGE_TYPES:
            continue
        name = str(entry["Surface"])
        if name not in difference[change_type]:
            elsewhere = [
                other
                for other in _DIRECTIONS
                if name in difference[other]
            ]
            detail = (
                f" the manifest shows it under {elsewhere} instead"
                if elsewhere
                else " the manifest does not show this name at all"
            )
            failures.append(
                f"{entry['fragment']} claims `{change_type}` for {name} but"
                f"{detail}."
            )

    assert not failures, "\n".join(failures)


# --- 4. Non-public entries are genuinely non-public ------------------------


def test_no_non_public_entry_appears_in_the_diff() -> None:
    """The assertion that keeps the classification honest.

    Together with assertion 2 this closes ``Public surface`` in both
    directions: a public change cannot hide as non-public (assertion 2), and a
    non-public entry cannot name something the manifest actually moved (here).
    """
    difference = _diff()
    moved = set().union(*(difference[key] for key in _DIRECTIONS))
    _, non_public = _partitions()

    offenders = [
        f"{entry['fragment']} :: {entry['Surface']}"
        for entry in non_public
        if entry["Surface"] in moved
    ]
    assert not offenders, (
        "these entries are classified `Public surface: false` but their"
        " `Surface` string appears in the generated manifest diff, which only"
        f" ever contains public Python names: {offenders}"
    )


# --- 5. The required behavior surface is present --------------------------


def test_the_required_behavior_surfaces_are_recorded() -> None:
    """``behavior`` is the one class exempt from diff agreement.

    Without a named required member, the exemption would let D-02's entry go
    missing and fail only a human read.
    """
    public, _ = _partitions()
    recorded = {
        str(entry["Surface"])
        for entry in public
        if entry["Change type"] == "behavior"
    }
    missing = sorted(_REQUIRED_BEHAVIOR_SURFACES - recorded)
    assert not missing, (
        f"the curated log carries no `behavior` entry for {missing}. These are"
        " the changes a signature diff cannot see, so nothing but this"
        " assertion would notice them going missing."
    )


# --- 6. Baseline immutability ---------------------------------------------


def test_the_frozen_baseline_is_byte_identical_to_what_15_01_committed() -> None:
    """The "before" side of Criterion 6 is immutable, or the diff is a lie.

    Overwriting the baseline with the current surface would make every
    assertion above pass against an empty diff — which is why assertion 1
    exists as well, and why this one pins bytes rather than shape.
    """
    digest = hashlib.sha256(_FROZEN_BASELINE.read_bytes()).hexdigest()
    assert digest == _BASELINE_DIGEST, (
        f"{_FROZEN_BASELINE} has changed. It is the immutable phase-start"
        " record and the 'before' side of ROADMAP Success Criterion 6;"
        " regenerating it destroys the comparison rather than refreshing it."
        f" Expected {_BASELINE_DIGEST}, got {digest}."
    )


def test_the_frozen_baseline_was_written_only_by_plan_15_01() -> None:
    """The history says the same thing the digest does, independently.

    The digest pins the bytes; this pins the *provenance*, which a future
    editor updating the digest constant would not also be able to fake. Skipped
    rather than failed where git is unavailable — a source checkout without
    history is a legitimate way to run the suite.
    """
    if shutil.which("git") is None:  # pragma: no cover - environment dependent
        return
    result = subprocess.run(
        [
            "git",
            "log",
            "--format=%s",
            "--",
            str(_FROZEN_BASELINE.relative_to(_REPO_ROOT)),
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:  # pragma: no cover - environment dependent
        return
    subjects = [line for line in result.stdout.splitlines() if line.strip()]
    if not subjects:  # pragma: no cover - shallow clone
        return
    foreign = [subject for subject in subjects if "(15-01)" not in subject]
    assert not foreign, (
        "the frozen baseline has commits from plans other than 15-01:"
        f" {foreign}. It is written once, at phase start, and never again."
    )
