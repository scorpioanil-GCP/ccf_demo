"""SEC-020 — the combined proof Dave set as the row's closure condition. SEC-020 is OPEN.

Dave, 2026-10-07, verbatim: *"prove withheld and nonexistent subjects are
indistinguishable across responses, refusal codes, public references,
composite paths and authorized record reads. Keep SEC-020 open until that
combined proof passes."* This module is that proof, written against public
behavior only; ``tests/products/sec020_worlds.py`` builds the deployments and
the doors. It is the closure gate: SEC-020 may be closed only on a run of this
module with no failure and no ``pending API`` skip.

How to read one test id
-----------------------
``test_withheld_is_indistinguishable[<comparison>-<shape>-<anchor>-<door>-<channel>]``

* ``comparison`` — ``cf``: two deployments identical except whether the data
  source holds the subject, both asked the same question about it by the same
  principal (the subject's own record says it sits in a restricted book, and
  the policy withholds such a subject from the asker); ``same``: one deployment
  whose source holds the subject, asked about it and about an identifier no
  source has ever held (the ``D-IMPL-371`` formulation).
* ``shape`` — the source shape: ``subject_keyed`` (the paved road),
  ``no_acquisition`` (a fabric holding the source before any question),
  ``population`` (an acquisition that reads everything, whatever is asked),
  ``similarity_refreshed`` (a similarity operator over an entity the
  acquisition refreshed), ``composite_subject_child`` /
  ``composite_fixed_child`` (a composite whose child is asked about the
  composite's own subject, or about a fixed one), ``reused_fabric`` (one fabric
  answering a question about the subject and then one about an unheld
  identifier) and ``reused_store`` (one persisted store, a fresh handle per
  question): both expected refused, Dave's Q9.
* ``anchor`` — the class's TTL anchor, ``from_decision`` or
  ``from_entity_freshness``.
* ``door`` — ``in_process``, ``http`` (the shipped API), ``mcp`` (the shipped
  product door; record reads through the artifact server and the Experience
  server's replay-record tool).
* ``channel`` — ``response`` (status and every byte the caller receives but
  the references), ``refusal`` (outcome, kind, reason, key, HTTP status, MCP
  error flag, and the cause the fabric RECORDED), ``reference`` (every
  reference the caller receives), ``composite`` (a composite's child rows as
  recorded), ``record`` (what the owner, and another principal of the same
  tenant, read back through every governed read path).

A failure names the differing paths. Each comparison carries a noise floor —
a second, independent copy of the nonexistent side — and a path that differs
there too is not counted (it is reported). Every channel has an instrument
(``test_the_instrument_sees_a_difference``): a side that must differ from the
nonexistent one, or the comparison could not see what it claims to compare.

Cells that need a public knob that does not exist yet are SKIPPED with the
reason ``pending API: <name>``; they run unchanged once the knob exists under
its documented name. Never xfail, never pass.

Dave's ruling D1 = (a) (2026-10-07 21:15 MST; verbatim beside ``sec020_worlds.D1A_RULING``)
-----------------------------------------------------------------------------------------
For a product that reads the whole population — the fabric loaded before the
question and walked by class (``no_acquisition``), the source that returns
everyone (``population``, ``early_population``, ``population_declared``) — the
two-deployment test cannot pass whatever the withholding mechanism, because an
identifier that exists in NEITHER deployment is already answered differently by
the two (measured by the lane's confound probe). For those shapes only, the
``D-IMPL-371`` comparison — the withheld subject against an identifier nothing
holds, in the same deployment — is the governing check for EVERY observable,
the record read back included; their two-deployment cells are RETIRED from this
gate, listed by id in :data:`RETIRED_D1A`, and pinned by
``test_d1a_retires_exactly_the_population_reading_counterfactual_cells``. They
are not generated, so they are neither skipped nor xfailed: a retired cell is
out of the gate, by name, with the ruling beside it. Every other shape keeps
Dave's two-deployment test as written. The same-deployment comparison of the
population-reading shapes has its own instrument
(``test_the_same_deployment_instrument_sees_a_difference``).

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Iterator
from typing import Any

import pytest

from tests.products import sec020_worlds as w

#: The MCP SDK and its HTTP client log every request at INFO; the proof reads
#: its own observations, so the module quiets them while it runs, and restores them.
_QUIETED_LOGGERS = ("mcp", "httpx")


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> Iterator[w.RunCache]:
    """One run per (shape, anchor, door) for this module; every channel's test reads it."""
    levels = {name: logging.getLogger(name).level for name in _QUIETED_LOGGERS}
    for name in _QUIETED_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        yield w.RunCache(lambda name: pathlib.Path(tmp_path_factory.mktemp(name)))
    finally:
        for name, level in levels.items():
            logging.getLogger(name).setLevel(level)


#: Every shape the matrix asks on: the seven the brief names (with the reused
#: fabric in its two forms), then the shapes whose public knob is pending.
ALL_SHAPES = (*w.SHAPES, *w.PENDING_SHAPES)

#: The two-deployment (``cf``) cells RETIRED from the closure gate by Dave's
#: D1 = (a) and ``D-IMPL-371`` (``sec020_worlds.D1A_RULING``; the ruling's text
#: is quoted verbatim in the comment above that constant).
#: For each, the same-deployment cell of the same shape, anchor, door and
#: channel governs instead. Listed explicitly so that what left the gate is
#: readable here, and pinned against the matrix's own channel rule by
#: ``test_d1a_retires_exactly_the_population_reading_counterfactual_cells``.
RETIRED_D1A: tuple[str, ...] = (
    "cf-no_acquisition-from_decision-in_process-response",
    "cf-no_acquisition-from_decision-in_process-refusal",
    "cf-no_acquisition-from_decision-in_process-reference",
    "cf-no_acquisition-from_decision-http-response",
    "cf-no_acquisition-from_decision-http-refusal",
    "cf-no_acquisition-from_decision-http-reference",
    "cf-no_acquisition-from_decision-http-record",
    "cf-no_acquisition-from_decision-mcp-response",
    "cf-no_acquisition-from_decision-mcp-refusal",
    "cf-no_acquisition-from_decision-mcp-reference",
    "cf-no_acquisition-from_decision-mcp-record",
    "cf-no_acquisition-from_entity_freshness-in_process-response",
    "cf-no_acquisition-from_entity_freshness-in_process-refusal",
    "cf-no_acquisition-from_entity_freshness-in_process-reference",
    "cf-no_acquisition-from_entity_freshness-http-response",
    "cf-no_acquisition-from_entity_freshness-http-refusal",
    "cf-no_acquisition-from_entity_freshness-http-reference",
    "cf-no_acquisition-from_entity_freshness-http-record",
    "cf-no_acquisition-from_entity_freshness-mcp-response",
    "cf-no_acquisition-from_entity_freshness-mcp-refusal",
    "cf-no_acquisition-from_entity_freshness-mcp-reference",
    "cf-no_acquisition-from_entity_freshness-mcp-record",
    "cf-population-from_decision-in_process-response",
    "cf-population-from_decision-in_process-refusal",
    "cf-population-from_decision-in_process-reference",
    "cf-population-from_decision-http-response",
    "cf-population-from_decision-http-refusal",
    "cf-population-from_decision-http-reference",
    "cf-population-from_decision-http-record",
    "cf-population-from_decision-mcp-response",
    "cf-population-from_decision-mcp-refusal",
    "cf-population-from_decision-mcp-reference",
    "cf-population-from_decision-mcp-record",
    "cf-population-from_entity_freshness-in_process-response",
    "cf-population-from_entity_freshness-in_process-refusal",
    "cf-population-from_entity_freshness-in_process-reference",
    "cf-population-from_entity_freshness-http-response",
    "cf-population-from_entity_freshness-http-refusal",
    "cf-population-from_entity_freshness-http-reference",
    "cf-population-from_entity_freshness-http-record",
    "cf-population-from_entity_freshness-mcp-response",
    "cf-population-from_entity_freshness-mcp-refusal",
    "cf-population-from_entity_freshness-mcp-reference",
    "cf-population-from_entity_freshness-mcp-record",
    "cf-early_population-from_decision-in_process-response",
    "cf-early_population-from_decision-in_process-refusal",
    "cf-early_population-from_decision-in_process-reference",
    "cf-early_population-from_decision-http-response",
    "cf-early_population-from_decision-http-refusal",
    "cf-early_population-from_decision-http-reference",
    "cf-early_population-from_decision-http-record",
    "cf-early_population-from_decision-mcp-response",
    "cf-early_population-from_decision-mcp-refusal",
    "cf-early_population-from_decision-mcp-reference",
    "cf-early_population-from_decision-mcp-record",
    "cf-early_population-from_entity_freshness-in_process-response",
    "cf-early_population-from_entity_freshness-in_process-refusal",
    "cf-early_population-from_entity_freshness-in_process-reference",
    "cf-early_population-from_entity_freshness-http-response",
    "cf-early_population-from_entity_freshness-http-refusal",
    "cf-early_population-from_entity_freshness-http-reference",
    "cf-early_population-from_entity_freshness-http-record",
    "cf-early_population-from_entity_freshness-mcp-response",
    "cf-early_population-from_entity_freshness-mcp-refusal",
    "cf-early_population-from_entity_freshness-mcp-reference",
    "cf-early_population-from_entity_freshness-mcp-record",
    "cf-population_declared-from_decision-in_process-response",
    "cf-population_declared-from_decision-in_process-refusal",
    "cf-population_declared-from_decision-in_process-reference",
    "cf-population_declared-from_decision-http-response",
    "cf-population_declared-from_decision-http-refusal",
    "cf-population_declared-from_decision-http-reference",
    "cf-population_declared-from_decision-http-record",
    "cf-population_declared-from_decision-mcp-response",
    "cf-population_declared-from_decision-mcp-refusal",
    "cf-population_declared-from_decision-mcp-reference",
    "cf-population_declared-from_decision-mcp-record",
    "cf-population_declared-from_entity_freshness-in_process-response",
    "cf-population_declared-from_entity_freshness-in_process-refusal",
    "cf-population_declared-from_entity_freshness-in_process-reference",
    "cf-population_declared-from_entity_freshness-http-response",
    "cf-population_declared-from_entity_freshness-http-refusal",
    "cf-population_declared-from_entity_freshness-http-reference",
    "cf-population_declared-from_entity_freshness-http-record",
    "cf-population_declared-from_entity_freshness-mcp-response",
    "cf-population_declared-from_entity_freshness-mcp-refusal",
    "cf-population_declared-from_entity_freshness-mcp-reference",
    "cf-population_declared-from_entity_freshness-mcp-record",
)


def _require(shape: str) -> None:
    """Skip a cell whose shape needs a public knob that does not exist yet — never xfail, never pass."""
    if shape in w.PENDING_SHAPES:
        name, exists = w.PENDING_SHAPES[shape]
        if not exists():
            pytest.skip(f"pending API: {name}")


def _cells() -> list[Any]:
    cells = []
    for shape in ALL_SHAPES:
        for comparison in w.comparisons_for(shape):
            for anchor in w.ANCHORS:
                for door in w.DOORS:
                    for channel in w.channels_for(comparison=comparison, shape=shape, door=door):
                        cells.append(
                            pytest.param(
                                comparison, shape, anchor, door, channel,
                                id=f"{comparison}-{shape}-{anchor}-{door}-{channel}",
                            )
                        )
    return cells


def _compare(run: w.Run, *, comparison: str, channel: str) -> tuple[set[str], set[str], Any, Any]:
    """Differing paths (noise floor removed), the floor itself, and the two values."""
    withheld_side, nonexistent_side, floor_side = w.PAIRS[comparison]
    withheld = run.channel(withheld_side, channel, comparison=comparison)
    nonexistent = run.channel(nonexistent_side, channel, comparison=comparison)
    floor = w.diff_paths(nonexistent, run.channel(floor_side, channel, comparison=comparison))
    return w.diff_paths(withheld, nonexistent) - floor, floor, withheld, nonexistent


@pytest.mark.parametrize(("comparison", "shape", "anchor", "door", "channel"), _cells())
def test_withheld_is_indistinguishable(
    runs: w.RunCache, comparison: str, shape: str, anchor: str, door: str, channel: str
) -> None:
    """What the caller observes for the WITHHELD subject equals what it observes for the NONEXISTENT one."""
    _require(shape)
    run = runs.get(shape=shape, anchor=anchor, door=door)
    differing, floor, withheld, nonexistent = _compare(run, comparison=comparison, channel=channel)
    assert not differing, (
        f"SEC-020 [{comparison}, {shape}, {anchor}, {door}, {channel}]: a withheld subject is"
        f" distinguishable from a nonexistent one at {sorted(differing)}"
        f" (noise floor, not counted: {sorted(floor)})\n"
        f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
    )


def _instruments() -> list[Any]:
    """Every channel any cell compares, per (shape, anchor, door), plus the name-only reference.

    A composite with a FIXED child asks that child about the same fixed subject
    in every deployment, so its child rows cannot differ by construction: that
    one channel has no instrument of its own and is instrumented by the
    subject-keyed composite, through the same extraction.
    """
    params = []
    for shape in ALL_SHAPES:
        for anchor in w.ANCHORS:
            for door in w.DOORS:
                channels: set[str] = set()
                for comparison in w.comparisons_for(shape):
                    channels |= set(w.channels_for(comparison=comparison, shape=shape, door=door))
                for channel in sorted(channels):
                    if shape in w.FIXED_CHILD_SHAPES and channel == w.COMPOSITE:
                        continue
                    params.append(pytest.param(shape, anchor, door, channel, False,
                                               id=f"{shape}-{anchor}-{door}-{channel}"))
                if w.SAME_DEPLOYMENT in w.comparisons_for(shape):
                    params.append(pytest.param(shape, anchor, door, w.REFERENCE, True,
                                               id=f"{shape}-{anchor}-{door}-reference-name-only"))
    return params


@pytest.mark.parametrize(("shape", "anchor", "door", "channel", "names_only"), _instruments())
def test_the_instrument_sees_a_difference(
    runs: w.RunCache, shape: str, anchor: str, door: str, channel: str, names_only: bool
) -> None:
    """The instrument: a side that differs from the nonexistent one MUST be seen to differ.

    ``response``, ``reference``, ``composite``, ``record``: the subject SERVED
    (the same deployment with the policy off) against the nonexistent side.
    ``refusal``: the nonexistent side asked the same question with a parameter
    its class does not declare, which the request contract refuses, against the
    nonexistent side. Paths in the counterfactual noise floor are not counted.
    Where the owner-read allowlist exists, the record channel's pair is built
    with the class listed, so default-deny cannot blind the instrument.
    """
    _require(shape)
    run = runs.get(shape=shape, anchor=anchor, door=door)
    left_side, right_side = w.instrument_pair(channel, run)
    left = run.channel(left_side, channel, names_only=names_only)
    right = run.channel(right_side, channel, names_only=names_only)
    floor = w.diff_paths(right, run.channel(w.CF_FLOOR, channel, names_only=names_only))
    seen = w.diff_paths(left, right) - floor
    assert seen, (
        f"instrument broken [{shape}, {anchor}, {door}, {channel}, names_only={names_only}]:"
        f" {left_side} and {right_side} are indistinguishable on this channel, so a PASS of its"
        f" comparison would prove nothing\n  {left_side}: {w.render(left)}\n  {right_side}: {w.render(right)}"
    )


def _served(run: w.Run, side: str, position: str) -> bool:
    """Whether ``side``'s question at ``position`` was SERVED, read off what its door returned."""
    response = run.channel(side, w.RESPONSE)[position]
    if run.door == w.IN_PROCESS:
        return response.get("outcome") == "served"
    if run.door == w.HTTP:
        return response.get("status") == 200
    outcome = response.get("outcome")
    return not response.get("is_error") and isinstance(outcome, dict) and outcome.get("refusal") is None


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
@pytest.mark.parametrize("shape", w.REUSED_SHAPES)
def test_a_fabric_reused_across_questions_is_refused(runs: w.RunCache, shape: str, anchor: str, door: str) -> None:
    """Dave, Q9: *"Enforce a fresh fabric per question whenever acquisition exists, including concurrent use."*

    One fabric with an acquisition seam (``reused_fabric``: one handle; or
    ``reused_store``: one persisted store, a fresh handle per question) is asked
    about the subject and then about an identifier it never held. The second
    question must not be SERVED from a graph the first one wrote into — refused
    by name, or the composition refused outright — in the deployment whose
    source holds the subject and in the one whose source does not.
    """
    run = runs.get(shape=shape, anchor=anchor, door=door)
    served = {side: _served(run, side, "second") for side in (w.CF_WITHHELD, w.CF_NONEXISTENT)}
    assert not any(served.values()), (
        f"[{shape}, {anchor}, {door}] a graph an acquisition seam wrote into answered a second question"
        f" (served: {served}); the second answer:\n"
        f"  holding:     {w.render(run.channel(w.CF_WITHHELD, w.RESPONSE)['second'])}\n"
        f"  not holding: {w.render(run.channel(w.CF_NONEXISTENT, w.RESPONSE)['second'])}"
    )


#: The shapes whose withholding deployment is asked three different questions.
UNIQUENESS_SHAPES = tuple(shape for shape in ALL_SHAPES if w.SAME_DEPLOYMENT in w.comparisons_for(shape))


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
@pytest.mark.parametrize("shape", UNIQUENESS_SHAPES)
def test_a_public_reference_never_names_two_records(runs: w.RunCache, shape: str, anchor: str, door: str) -> None:
    """Dave, Q11: *"Equal public references must not identify different immutable record contents."*

    In ONE deployment, three questions with three different subjects are three
    different decisions, and each record holds its own request; so the
    references the caller receives for them must be pairwise different, at
    every door, served and refused alike.
    """
    _require(shape)
    run = runs.get(shape=shape, anchor=anchor, door=door)
    answered = {
        side: run.channel(side, w.REFERENCE)
        for side in (w.CF_WITHHELD, w.SAME_NONEXISTENT, w.SAME_FLOOR)
    }
    # A question that raised, or a door that could not be reached, handed out no
    # reference at all; it is not a decision with a reference to compare.
    references = {
        side: w.render(value, limit=10_000)
        for side, value in answered.items()
        if not (isinstance(value, dict) and value.get("outcome") in ("raised", "unreachable"))
    }
    assert len(references) >= 2, (
        f"[{shape}, {anchor}, {door}] fewer than two of the three questions handed out a reference,"
        f" so uniqueness cannot be measured: {answered}"
    )
    assert len(set(references.values())) == len(references), (
        f"[{shape}, {anchor}, {door}] two decisions about different subjects carry one public"
        f" reference: {references}"
    )


#: The shapes the record channel is held on when a withholding class is listed.
LISTED_SHAPES = (w.SUBJECT_KEYED, w.COMPOSITE_SUBJECT_CHILD)


@pytest.mark.parametrize("door", (w.HTTP, w.MCP))
@pytest.mark.parametrize("anchor", w.ANCHORS)
@pytest.mark.parametrize("shape", LISTED_SHAPES)
def test_a_withholding_class_listed_evidence_readable_does_not_reopen_the_record(
    runs: w.RunCache, shape: str, anchor: str, door: str
) -> None:
    """Dave, Q12: *"Default-deny owner read-back, with an explicit tenant class allowlist. Reject withholding classes."*

    PENDING until the allowlist exists under its documented name. Both
    deployments LIST the class whose Π withholds the subject; what the owner,
    and another principal, read back must still be indistinguishable — the
    listing rejected, or the reads refused alike.
    """
    if not w.evidence_allowlist_exists():
        pytest.skip(f"pending API: {w.EVIDENCE_ALLOWLIST_FIELD} (ProductEntitlementPolicy)")
    run = runs.get(shape=shape, anchor=anchor, door=door)
    withheld = run.channel(w.WITHHELD_READABLE, w.RECORD)
    nonexistent = run.channel(w.NONEXISTENT_READABLE, w.RECORD)
    differing = w.diff_paths(withheld, nonexistent)
    assert not differing, (
        f"[{shape}, {anchor}, {door}] with the withholding class listed evidence-readable, the record"
        f" read back differs at {sorted(differing)}\n  withheld: {w.render(withheld)}\n"
        f"  nonexistent: {w.render(nonexistent)}"
    )


def test_pending_api_caller_visible_reference() -> None:
    """Dave, Q11: *"Use a caller-visible reference separate from the internal evidence address."*

    No cell above needs this reference's name: every reference cell compares
    whatever reference each door hands out, so it measures the new reference
    unchanged when it lands. This marker exists because the reference's public
    name and its read route are not documented on ``e9e5e2cd`` (lane
    ``378-s020record`` PROPOSAL, option 2-B, names none): the gate cannot be
    read as complete until the coordinator confirms the record cells present
    the reference the doors actually hand out to the route that resolves it,
    and replaces this marker with that route's cells.
    """
    pytest.skip("pending API: caller-visible replay reference and its read route (Q11; no public name documented)")


def test_d1a_retires_exactly_the_population_reading_counterfactual_cells() -> None:
    """D1 = (a), held: the retired cells are exactly the population-reading shapes' two-deployment cells.

    And each of them has a governing same-deployment cell in the gate — for every
    observable those two-deployment cells covered — while every other shape
    keeps the two-deployment test as written. Retirement is by name, never by
    xfail or by a skip.
    """
    expected = [
        f"{w.COUNTERFACTUAL}-{shape}-{anchor}-{door}-{channel}"
        for shape in w.POPULATION_READING_SHAPES
        for anchor in w.ANCHORS
        for door in w.DOORS
        for channel in w.channels_for(comparison=w.COUNTERFACTUAL, shape=shape, door=door)
    ]
    assert len(RETIRED_D1A) == len(set(RETIRED_D1A)), "a retired cell is listed twice"
    assert sorted(RETIRED_D1A) == sorted(expected), (
        "the retired list is not the population-reading shapes' two-deployment cells:"
        f" missing {sorted(set(expected) - set(RETIRED_D1A))},"
        f" extra {sorted(set(RETIRED_D1A) - set(expected))}"
    )
    gate = {param.id for param in _cells()}
    assert not set(RETIRED_D1A) & gate, (
        f"a retired cell is still in the closure gate: {sorted(set(RETIRED_D1A) & gate)}"
    )
    ungoverned = [
        cell for cell in RETIRED_D1A
        if f"{w.SAME_DEPLOYMENT}-{cell.removeprefix(w.COUNTERFACTUAL + '-')}" not in gate
    ]
    assert not ungoverned, f"a retired cell has no governing same-deployment cell: {ungoverned}"
    for shape in ALL_SHAPES:
        if shape in w.POPULATION_READING_SHAPES:
            assert w.comparisons_for(shape) == (w.SAME_DEPLOYMENT,), shape
        elif shape in w.REUSED_SHAPES:
            assert w.comparisons_for(shape) == (w.COUNTERFACTUAL,), shape
        else:
            assert w.comparisons_for(shape) == w.COMPARISONS, (
                f"{shape} is not population-reading and must keep the two-deployment test"
            )


def _same_instruments() -> list[Any]:
    params = []
    for shape in w.POPULATION_READING_SHAPES:
        for anchor in w.ANCHORS:
            for door in w.DOORS:
                for channel in w.channels_for(comparison=w.SAME_DEPLOYMENT, shape=shape, door=door):
                    params.append(pytest.param(shape, anchor, door, channel, id=f"{shape}-{anchor}-{door}-{channel}"))
    return params


@pytest.mark.parametrize(("shape", "anchor", "door", "channel"), _same_instruments())
def test_the_same_deployment_instrument_sees_a_difference(
    runs: w.RunCache, shape: str, anchor: str, door: str, channel: str
) -> None:
    """D1 = (a)'s comparison, instrumented in ONE deployment: two questions it must tell apart.

    The deployment that SERVES the subject (policy off) is asked about the
    subject and about an identifier nothing holds; for refusal codes and the
    reference, the never-held question carrying a parameter its class does not
    declare (refused by contract, so it reads nothing) is set against the valid
    one. Compared exactly as the same-deployment cells compare — the asked
    identifiers neutralized, references by record name, the same-deployment
    noise floor not counted.
    """
    _require(shape)
    run = runs.get(shape=shape, anchor=anchor, door=door)
    left_side, right_side = w.SAME_INSTRUMENT_PAIRS[channel]
    same = w.SAME_DEPLOYMENT
    left = run.channel(left_side, channel, comparison=same)
    right = run.channel(right_side, channel, comparison=same)
    floor = w.diff_paths(
        run.channel(w.SAME_NONEXISTENT, channel, comparison=same),
        run.channel(w.SAME_FLOOR, channel, comparison=same),
    )
    seen = w.diff_paths(left, right) - floor
    assert seen, (
        f"same-deployment instrument broken [{shape}, {anchor}, {door}, {channel}]: {left_side} and"
        f" {right_side} are indistinguishable on this channel, so a PASS of its same-deployment"
        f" comparison would prove nothing\n  {left_side}: {w.render(left)}\n  {right_side}: {w.render(right)}"
    )
