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

import pytest

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


def _export_shapes(document: dict[str, Any]) -> dict[str, Any]:
    """Every fully-qualified export a surface document records, with its shape."""
    return {
        f"{module}.{name}": shape
        for module, entry in document.items()
        for name, shape in entry["exports"].items()
    }


def restored_surfaces() -> set[str]:
    """Names the log ``reshaped`` **back to the shape the baseline froze**.

    The mirror of :func:`short_lived_surfaces`, for a reshape rather than a
    birth. A name whose signature a plan changed and a later plan changed back
    appears in **no** partition of ``diff(baseline, live)``: it is in both
    documents and its shape is the same in both, so there is nothing for the
    diff to report. The record is honest and complete — every fragment along the
    way claims ``reshaped``, and each was true when it was written — and the diff
    simply cannot see a round trip.

    ``ccf.products.gates.run_federated_gates`` is the first such name.
    ``24.5-13`` gave it ``debt_tolerance`` and ``24.5-15`` gave it
    ``empty_results``; ``24.6-04`` retired the first (``D-IMPL-251`` C1=A) and
    ``24.6-05`` the second (``D-IMPL-242`` amendment 1), which returned the
    signature to its Phase-15 form character for character.

    **Derived, never listed**, on :func:`short_lived_surfaces`' reasoning: a
    hand-maintained allowance rots and invites editing to silence a failure.

    **Two conditions, and the second is what keeps this from being a hole.**
    The shape condition alone would admit a fragment that claimed ``reshaped``
    for a name nothing ever touched — a false claim, which the gate used to
    catch. So a name also needs **at least two** ``reshaped`` claims against it:
    a signature cannot return to the baseline's without having left it, and
    leaving and returning are two claims by two plans. One fragment claiming a
    reshape that never happened still fails, exactly as before.

    An empty result is the ordinary state and admits nothing.
    """
    public, _ = _partitions()
    baseline: dict[str, Any] = json.loads(
        _FROZEN_BASELINE.read_text(encoding="utf-8")
    )
    return restored_from(
        public,
        frozen_shapes=_export_shapes(baseline),
        live_shapes=_export_shapes(build_surface()),
    )


def restored_from(
    entries: list[dict[str, object]],
    *,
    frozen_shapes: dict[str, Any],
    live_shapes: dict[str, Any],
) -> set[str]:
    """The derivation :func:`restored_surfaces` performs, over supplied inputs.

    Pure and parameterized so the controls below can hand it a fabricated log
    and watch it refuse — the discipline this module applies everywhere else:
    an allowance nobody has seen decline something is an allowance nobody has
    tested.
    """
    claims: dict[str, int] = {}
    for entry in entries:
        if str(entry["Change type"]) != "reshaped":
            continue
        name = str(entry["Surface"])
        claims[name] = claims.get(name, 0) + 1
    return {
        name
        for name, count in claims.items()
        if count >= 2
        and name in frozen_shapes
        and name in live_shapes
        and frozen_shapes[name] == live_shapes[name]
    }


def short_lived_surfaces() -> set[str]:
    """Names **born and buried inside** the frozen-baseline window.

    A name a later plan added and a later-still plan removed appears in
    **neither** side of ``diff(baseline, live)``: not in the baseline, because it
    did not exist when the baseline was frozen, and not in the live surface,
    because it is gone. The record is honest and complete — one fragment claims
    ``added``, another claims ``removed`` — and the diff simply cannot see
    either. ``17-06`` adding ``binding_document.ResolverCall`` and ``17-12``
    removing it under ``D-IMPL-141``'s ruling is the first such pair.

    **Derived, never listed.** A hand-maintained allowance list is a thing that
    rots and a thing a later executor edits to silence a failure. This is
    computed from the record itself, so the *pair of claims is the evidence*:
    a name qualifies only when the log carries both directions for it, and
    :func:`test_a_short_lived_name_is_absent_from_both_sides` then requires it to
    be genuinely absent from both surfaces. A mislabelled entry — ``removed``
    claimed for a name that is still live, or ``added`` for one that predates
    the baseline — fails that test rather than being admitted here.

    An empty result is the ordinary state and admits nothing.
    """
    public, _ = _partitions()
    added = {
        str(entry["Surface"])
        for entry in public
        if str(entry["Change type"]) == "added"
    }
    removed = {
        str(entry["Surface"])
        for entry in public
        if str(entry["Change type"]) == "removed"
    }
    return added & removed


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

    **A second pair is reconciled the same way: `reshaped` claimed for a name
    whose signature a later plan reshaped BACK to the baseline's own.** See
    :func:`restored_surfaces`. The round trip leaves the name in no partition
    of the diff at all, and the admission is not a tolerance: membership in
    that set *is* the measurement that the two documents agree about the name,
    so a name whose shape genuinely differs cannot enter it. Assertion 2 still
    holds the other direction, so a plan that reshapes a name and leaves it
    reshaped is unaffected.

    **One direction pair is reconciled rather than failed: `reshaped` claimed
    for a name the frozen baseline shows as `added`.** The baseline is frozen at
    *Phase 15 start* and never rewritten, so a name Phase 15 introduced can only
    ever appear in the ``added`` partition of this diff — including after a later
    cycle reshapes it. Phase 15.1 is that later cycle, and under the unreconciled
    rule its fragments could not classify a field addition to a Phase-15 class
    honestly: ``reshaped`` is unrepresentable and ``added`` would require a
    ``Before: absent`` the plan did not cause. The reconciliation is narrow and
    it weakens nothing, because assertion 2 above still holds the other
    direction: every ``added`` name must still be claimed by *some* public entry
    carrying ``added``, so a plan that genuinely adds a name and claims only
    ``reshaped`` still fails, there. What is admitted here is only the case where
    the name **is** in the diff and the direction is pinned by an immutable
    before-side older than the name itself.
    """
    difference = _diff()
    failures: list[str] = []
    public, _ = _partitions()
    short_lived = short_lived_surfaces()
    restored = restored_surfaces()

    for entry in public:
        change_type = str(entry["Change type"])
        if change_type in _DIFF_EXEMPT_CHANGE_TYPES:
            continue
        name = str(entry["Surface"])
        if change_type == "reshaped" and name in difference["added"]:
            continue
        if name in short_lived and change_type in {"added", "removed"}:
            continue
        if change_type == "reshaped" and name in restored:
            continue
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


def _exported_names(document: dict[str, Any]) -> set[str]:
    """Every fully-qualified export a surface document records."""
    return {
        f"{module}.{name}"
        for module, entry in document.items()
        for name in entry["exports"]
    }


def assert_short_lived_names_are_absent_from_both_sides(names: set[str]) -> None:
    """The check that makes :func:`short_lived_surfaces` an allowance, not a hole.

    A name is admitted there only because the log claims it in **both**
    directions. That claim is checkable against reality, and this checks it: a
    genuinely short-lived name is in neither the frozen baseline nor the live
    surface. If it is in the baseline it predates the window and the ``added``
    claim is wrong; if it is live it was never removed and the ``removed`` claim
    is wrong. Either way the pair is a mislabelling, and admitting it would have
    let two wrong entries cancel each other out.

    Takes ``names`` as a **parameter** so the control below can hand this
    function a divergent subject and be watched failing. An assertion only ever
    run against the one honest subject is an assertion nobody has seen work.
    """
    baseline: dict[str, Any] = json.loads(
        _FROZEN_BASELINE.read_text(encoding="utf-8")
    )
    baseline_names = _exported_names(baseline)
    live_names = _exported_names(build_surface())

    offenders = [
        f"{name} —{' in the frozen baseline' if name in baseline_names else ''}"
        f"{' and' if name in baseline_names and name in live_names else ''}"
        f"{' still in the live surface' if name in live_names else ''}"
        for name in sorted(names)
        if name in baseline_names or name in live_names
    ]
    assert not offenders, (
        "these names are claimed both `added` and `removed` by the log, which"
        " admits them from the diff cross-check — but they are not short-lived:"
        f" {offenders}"
    )


def test_a_short_lived_name_is_absent_from_both_sides() -> None:
    """The honest subject: every derived short-lived name is genuinely gone."""
    assert_short_lived_names_are_absent_from_both_sides(short_lived_surfaces())


def test_the_short_lived_check_fires_on_a_name_that_is_still_live() -> None:
    """CONTROL — a name the log would claim gone while the tree still exports it.

    Fed to the **shipped** assertion, not to a re-implementation of it. Without
    this the allowance in
    :func:`test_every_public_log_entry_has_a_matching_diff_line` would rest on a
    check nobody had seen refuse anything.
    """
    live = sorted(_exported_names(build_surface()))
    assert live, "the live surface is empty — this control has no subject"

    with pytest.raises(AssertionError) as fired:
        assert_short_lived_names_are_absent_from_both_sides({live[0]})

    message = str(fired.value)
    assert live[0] in message
    assert "still in the live surface" in message


def test_the_short_lived_check_fires_on_a_name_older_than_the_baseline() -> None:
    """CONTROL — a name that predates the window, so its `added` claim is wrong."""
    baseline: dict[str, Any] = json.loads(
        _FROZEN_BASELINE.read_text(encoding="utf-8")
    )
    frozen = sorted(_exported_names(baseline))
    assert frozen, "the frozen baseline is empty — this control has no subject"

    with pytest.raises(AssertionError) as fired:
        assert_short_lived_names_are_absent_from_both_sides({frozen[0]})

    assert "in the frozen baseline" in str(fired.value)


def assert_restored_names_have_the_baselines_own_shape(names: set[str]) -> None:
    """The check that makes :func:`restored_surfaces` an allowance, not a hole.

    A name is admitted there because the two surface documents agree about its
    shape. That agreement is checkable, and this checks it independently of the
    derivation: a name missing from either document, or carrying a different
    shape in the two, is not a round trip and admitting it would let a real
    reshape pass unclaimed.

    Takes ``names`` as a **parameter** so the controls below can hand this
    function a divergent subject and be watched failing — the discipline this
    module already applies to the short-lived pair.
    """
    baseline: dict[str, Any] = json.loads(
        _FROZEN_BASELINE.read_text(encoding="utf-8")
    )
    frozen_shapes = _export_shapes(baseline)
    live_shapes = _export_shapes(build_surface())

    offenders = []
    for name in sorted(names):
        if name not in frozen_shapes:
            offenders.append(f"{name} — absent from the frozen baseline")
        elif name not in live_shapes:
            offenders.append(f"{name} — absent from the live surface")
        elif frozen_shapes[name] != live_shapes[name]:
            offenders.append(
                f"{name} — the two documents disagree about its shape:"
                f" {frozen_shapes[name]} vs {live_shapes[name]}"
            )
    assert not offenders, (
        "these names are admitted from the diff cross-check as reshaped back"
        " to the baseline's own signature — but they are not restored:"
        f" {offenders}"
    )


def test_a_restored_name_has_the_baselines_own_shape() -> None:
    """The honest subject: every derived restored name really is a round trip."""
    assert_restored_names_have_the_baselines_own_shape(restored_surfaces())


def test_the_restored_check_fires_on_a_name_whose_shape_actually_moved() -> None:
    """CONTROL — a name the two documents genuinely disagree about.

    Fed to the **shipped** assertion. Without it the reconciliation in
    :func:`test_every_public_log_entry_has_a_matching_diff_line` would rest on
    a check nobody had seen refuse anything.
    """
    baseline: dict[str, Any] = json.loads(
        _FROZEN_BASELINE.read_text(encoding="utf-8")
    )
    frozen_shapes = _export_shapes(baseline)
    live_shapes = _export_shapes(build_surface())
    moved = sorted(
        name
        for name, shape in live_shapes.items()
        if name in frozen_shapes and frozen_shapes[name] != shape
    )
    assert moved, (
        "no name in the tree has a shape different from the baseline's — this"
        " control has no subject"
    )

    with pytest.raises(AssertionError) as fired:
        assert_restored_names_have_the_baselines_own_shape({moved[0]})

    assert "disagree about its shape" in str(fired.value)


def test_the_restored_check_fires_on_a_name_the_baseline_never_had() -> None:
    """CONTROL — a name added after the freeze, so `restored` is meaningless for it."""
    baseline: dict[str, Any] = json.loads(
        _FROZEN_BASELINE.read_text(encoding="utf-8")
    )
    frozen_shapes = _export_shapes(baseline)
    live_only = sorted(
        name for name in _export_shapes(build_surface()) if name not in frozen_shapes
    )
    assert live_only, "every live name predates the baseline — no subject"

    with pytest.raises(AssertionError) as fired:
        assert_restored_names_have_the_baselines_own_shape({live_only[0]})

    assert "absent from the frozen baseline" in str(fired.value)


def test_the_restored_check_admits_nothing_on_an_empty_set() -> None:
    """CONTROL — **the empty case**, stated rather than left to inference."""
    assert_restored_names_have_the_baselines_own_shape(set())


def test_a_single_reshape_claim_is_not_a_round_trip() -> None:
    """CONTROL — the derivation refuses a lone `reshaped` claim for an unmoved name.

    The hole the second condition closes, watched closing. A fragment that
    claimed a reshape which never happened would satisfy the shape comparison
    trivially — the name IS identical in both documents, because nothing
    touched it — and the reconciliation would silence a false record. One claim
    is refused; two are admitted. Both legs asserted, so the rule is measured
    rather than described.
    """
    shapes = {"pkg.mod.name": {"kind": "function", "shape": "()"}}
    one = [
        {"Surface": "pkg.mod.name", "Change type": "reshaped", "Public surface": True}
    ]

    assert (
        restored_from(one, frozen_shapes=shapes, live_shapes=shapes) == set()
    ), "a single reshape claim was admitted as a round trip"
    assert restored_from(
        one * 2, frozen_shapes=shapes, live_shapes=shapes
    ) == {"pkg.mod.name"}


def test_the_derivation_refuses_a_name_whose_shape_moved() -> None:
    """CONTROL — two claims are not enough when the shapes disagree."""
    two = [
        {"Surface": "pkg.mod.name", "Change type": "reshaped", "Public surface": True}
    ] * 2

    assert (
        restored_from(
            two,
            frozen_shapes={"pkg.mod.name": {"shape": "(a)"}},
            live_shapes={"pkg.mod.name": {"shape": "(a, b)"}},
        )
        == set()
    )


def test_the_short_lived_check_admits_nothing_on_an_empty_set() -> None:
    """CONTROL — **the empty case**, stated rather than left to inference.

    An empty set is the ordinary state once these names age out of the record,
    and it must pass while admitting nothing. That is asserted here so a future
    reader does not have to work out whether emptiness is safe.
    """
    assert_short_lived_names_are_absent_from_both_sides(set())


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
    """The history says the same thing the digest does, from a second source.

    The digest pins the bytes; this pins the *provenance*, so an editor who
    regenerated the baseline and updated the digest constant would still have
    to produce a commit whose subject names 15-01.

    **Stated honestly, because the strong version would be an over-claim**
    (raised by cross-AI review at the phase close): this keys on commit-subject
    text, not on a pinned commit hash, and it returns without asserting where
    git is absent or the history is shallow. Those are legitimate ways to run
    the suite, and a test that failed on them would be muted rather than fixed.
    It is corroboration for the digest, not an independently unfakeable
    provenance proof.
    """
    if shutil.which("git") is None:  # pragma: no cover - environment dependent
        return
    # Ask git whether the history is shallow rather than INFERRING it from an
    # empty log. A shallow clone does not return zero subjects — its grafted
    # root appears to introduce every file in the tree, so `git log -- <path>`
    # returns exactly ONE subject: HEAD's. The `if not subjects` guard below
    # therefore never fired, and this assertion compared HEAD's own subject
    # against "(15-01)" — unsatisfiable for every commit since that plan.
    #
    # It failed that way in CI on the first run that ever reached it
    # (31970398090, 2026-08-16): `actions/checkout@v4` defaults to
    # `fetch-depth: 1`, and the tests job had been dying at collection long
    # before this test, so a check that could never pass stayed invisible.
    # Reproduced with `git clone --depth 1`, which returns HEAD's subject here.
    #
    # The docstring's intent was already correct — skip where the history is
    # shallow. Only the detection was a guess; this is git's own answer.
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if shallow.returncode != 0:  # pragma: no cover - environment dependent
        return
    if shallow.stdout.strip() == "true":  # pragma: no cover - shallow clone
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
    if not subjects:  # pragma: no cover - unborn or path-less history
        return
    foreign = [subject for subject in subjects if "(15-01)" not in subject]
    assert not foreign, (
        "the frozen baseline has commits from plans other than 15-01:"
        f" {foreign}. It is written once, at phase start, and never again."
    )
