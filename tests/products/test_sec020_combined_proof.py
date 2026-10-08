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
  booted for a question, asked about the subject and then about an unheld
  identifier: the second question expected refused, ``AcquiredFabricReused``)
  and ``reused_store`` (one persisted store reopened by an ordinary boot for
  every question: every question expected refused,
  ``AcquisitionNeedsAQuestionFabric``) — Dave's Q9; ``early_*`` (the same
  shapes, the plan factory declaring the early-withholding policy,
  ``SubjectDisclosingPlanFactoryProtocol`` — Dave's Q8) and
  ``population_declared`` (the population fetched by the explicit population
  phase, ``open_product(population=...)`` — Dave's Q7).
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

Never green on two equal exceptions
-----------------------------------
Two sides that both RAISED instead of answering are equal on every channel,
and that equality says nothing about indistinguishability. A cell whose two
sides both raised fails as "not evidence", and an instrument with a side that
raised fails likewise — except where the refusal of the composition IS the
property under test, and only that refusal, named by type
(``sec020_worlds.REUSE_REFUSALS``): every question of every ``reused_store``
cell (``AcquisitionNeedsAQuestionFabric``) and the second question of every
``reused_fabric`` cell (``AcquiredFabricReused``). Behind HTTP (a 500) and MCP
(``ccf-runtime-failure:<id>``) the type is read off the resolver each door was
handed (``sec020_worlds.door_resolver``), so a builder that broke cannot pass
as refused. Where the owed ruling P2's option (c) is on the tree (a CANDIDATE,
not ruled), the two late-composite shapes declare no withholding stance and
every question of theirs is its construction refusal,
``CompositeNeedsAWithholdingStance`` (``sec020_worlds.CONSTRUCTION_REFUSALS``),
held the same way, with each instrument set against the same composite
declaring a stance (``sec020_worlds.DECLARED_TWIN``).

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

Dave's Q11 and Q12, as lane ``378b-s020record`` built them (adapted by lane ``378d-s020trial``)
-------------------------------------------------------------------------------------------------
Its PROPOSAL, section 7, names three things this proof needs once Q11 and Q12
are on the tree; this module and its worlds now do exactly those three:

1. The record channel's instrument is built in deployments whose tenant LISTS
   the class and whose class AFFIRMS ``subject_withholding: never``, policy
   off — served and nonexistent sides only, floored by a second nonexistent
   copy — because default-deny refuses every read of an unlisted class alike.
   The listed-class cell expects the two named refusals: a class that does not
   affirm ``never``, listed, is refused where its resolver is built
   (``WithholdingClassListedReadable``), and the withheld subject under a class
   that affirms it is refused before anything is recorded.
2. Each answer's reference is unique (a fresh issuance in every record), so a
   difference-based reference instrument cannot see past its own noise floor
   by design. It is replaced by Q11's property checks
   (``sec020_worlds.reference_properties``): the same question is handed
   different references; equal references never name different records; name
   = version = the record's content address.
3. The caller-visible reference has no new name: it IS the ``replay_ref`` /
   ``replay_reference`` each door hands out, and its read route is the governed
   evidence reads; the pending marker is replaced by a test that the record
   cells present that very reference to those routes and that they resolve it
   to its own record.

These adaptations decide nothing Dave has not ruled: E1 and E2 are OWED
(``records/2026-10-08-d-impl-378-ci-lane/OWED-RULINGS.md``). SEC-020 is OPEN.

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
    differing = w.diff_paths(withheld, nonexistent)
    # The floor excuses a difference in VALUE, never in KIND (``sec020_worlds.kind_diff_paths``):
    # under Q11 two nonexistent copies differ at every reference path, which must not
    # excuse a withheld side handed no reference where the nonexistent side was handed one.
    counted = (differing - floor) | (differing & floor & w.kind_diff_paths(withheld, nonexistent))
    return counted, floor, withheld, nonexistent


def _vacuous(run: w.Run, *sides: str, either: bool = False) -> dict[str, dict[str, str]]:
    """Positions where the named sides RAISED instead of answering, where raising is not the property.

    Two sides that both raised the same exception look alike on every channel —
    and that equality says nothing about whether a withheld subject is
    distinguishable from a nonexistent one. A cell is never green on it, except
    where the refusal of the composition is itself the property under test
    (:func:`~tests.products.sec020_worlds.raising_is_the_property`: the second
    question to a reused question fabric; every question to a reused store).
    ``either``: count a position where ANY named side raised (an instrument is
    not evidence when one of its sides broke), not only where all did.
    """
    raised = {side: run.raised(side) for side in sides}
    positions = set().union(*(set(r) for r in raised.values()))
    found: dict[str, dict[str, str]] = {}
    for position in sorted(positions):
        hit = {
            side: r[position]
            for side, r in raised.items()
            if position in r and not w.raising_is_the_property(run.shape, position, r[position])
        }
        if (either and hit) or (hit and all(position in r for r in raised.values())):
            found[position] = hit
    return found


@pytest.mark.parametrize(("comparison", "shape", "anchor", "door", "channel"), _cells())
def test_withheld_is_indistinguishable(
    runs: w.RunCache, comparison: str, shape: str, anchor: str, door: str, channel: str
) -> None:
    """What the caller observes for the WITHHELD subject equals what it observes for the NONEXISTENT one."""
    _require(shape)
    run = runs.get(shape=shape, anchor=anchor, door=door)
    withheld_side, nonexistent_side, _ = w.PAIRS[comparison]
    vacuous = _vacuous(run, withheld_side, nonexistent_side)
    assert not vacuous, (
        f"SEC-020 [{comparison}, {shape}, {anchor}, {door}, {channel}]: not evidence — both sides"
        f" RAISED instead of answering, and two equal exceptions are equal on every channel: {vacuous}"
    )
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
    if channel == w.REFERENCE and shape != w.REUSED_STORE and w.DECLARED_TWIN not in run.sides:
        # Q11: a reference is unique per answer, so no difference survives the
        # noise floor by design; the reference channel is instrumented by
        # Q11's properties instead (``reused_store``: Q9 refuses every
        # question of the two copies, and an undeclared composite under
        # P2 (c) every question, so those keep the structural pair below).
        problems = w.reference_properties(run)
        assert not problems, (
            f"reference instrument [{shape}, {anchor}, {door}, names_only={names_only}]: Dave's Q11"
            f" properties do not hold, so a PASS of the reference comparison would prove nothing: {problems}"
        )
        return
    left_side, right_side = w.instrument_pair(channel, run)
    vacuous = _vacuous(run, left_side, right_side, either=True)
    assert not vacuous, (
        f"instrument not evidence [{shape}, {anchor}, {door}, {channel}]: a side RAISED instead of"
        f" answering, so a difference it shows is the exception's, not the channel's: {vacuous}"
    )
    left = run.channel(left_side, channel, names_only=names_only)
    right = run.channel(right_side, channel, names_only=names_only)
    floor = w.diff_paths(right, run.channel(w.instrument_floor(channel, run), channel, names_only=names_only))
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

    One fabric with an acquisition seam is asked about the subject and then
    about an identifier it never held, in every deployment that asks (source
    holding the subject or not; policy on or off). ``reused_fabric`` (one handle
    booted for a question): the second question is refused by name,
    ``AcquiredFabricReused``. ``reused_store`` (one persisted store, an ordinary
    boot per question): never a question fabric, so EVERY question is refused,
    ``AcquisitionNeedsAQuestionFabric``. The refusal is read by TYPE at every
    door (behind HTTP and MCP, off the resolver the door was handed), so a
    builder that broke cannot pass as refused. The control: the question
    fabric answers the ONE question it was booted for (the serving deployment's
    first question is SERVED), so the second one's refusal is the reuse's.
    """
    run = runs.get(shape=shape, anchor=anchor, door=door)
    refusal, refused_at = w.REUSE_REFUSALS[shape]
    wrong: dict[str, Any] = {}
    for side in (w.CF_WITHHELD, w.CF_NONEXISTENT, w.CF_FLOOR, w.SERVED):
        for position in refused_at:
            raised = run.raised(side).get(position, "")
            if _served(run, side, position) or not raised.startswith(f"{refusal}:"):
                wrong[f"{side}:{position}"] = raised or w.render(run.channel(side, w.RESPONSE)[position])
    assert not wrong, (
        f"[{shape}, {anchor}, {door}] a reused fabric was not refused with {refusal} at {refused_at}: {wrong}"
    )
    if shape == w.REUSED_FABRIC:
        assert _served(run, w.SERVED, "first"), (
            f"[{shape}, {anchor}, {door}] control: the question fabric did not serve the one question it was"
            f" booted for, so the refusal of the second is not evidence about reuse:"
            f" {w.render(run.channel(w.SERVED, w.RESPONSE)['first'])}"
        )


#: The shapes P2 (c) refuses at construction on this tree (empty where the refusal does not exist).
UNDECLARED_COMPOSITE_SHAPES = tuple(shape for shape in w.CONSTRUCTION_REFUSALS if w.refused_at_construction(shape))


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
@pytest.mark.parametrize("shape", UNDECLARED_COMPOSITE_SHAPES)
def test_an_undeclared_composite_is_refused_where_its_resolver_is_built(
    runs: w.RunCache, shape: str, anchor: str, door: str
) -> None:
    """``D-IMPL-378`` owed ruling P2, option (c) — a CANDIDATE; Dave has not ruled P2.

    A composite whose stance is neither an early policy nor ``subject_withholding:
    never`` is refused where its resolver is built: every question of every
    deployment of this shape — whether its source holds the subject or not,
    whatever is asked — observes that ONE refusal, by name, at every door (read
    by type behind HTTP and MCP off the resolver each door was handed). This is
    the property the shape's matrix cells are held on, exactly as Q9's reuse
    refusals are for the reused shapes. The control: the same composite with an
    early policy declared is built and its question answered, so the refusal is
    the missing stance's, not a broken builder's.
    """
    run = runs.get(shape=shape, anchor=anchor, door=door)
    refusal = w.CONSTRUCTION_REFUSALS[shape]
    wrong = {
        side: run.raised(side).get(w.ONLY, "") or w.render(run.channel(side, w.RESPONSE))
        for side in (w.CF_WITHHELD, w.CF_NONEXISTENT, w.CF_FLOOR, w.SERVED, w.REFUSED_QUESTION,
                     w.SAME_NONEXISTENT, w.SAME_FLOOR)
        if not run.raised(side).get(w.ONLY, "").startswith(f"{refusal}:")
    }
    assert not wrong, f"[{shape}, {anchor}, {door}] not refused by {refusal}: {wrong}"
    assert not run.raised(w.DECLARED_TWIN), (
        f"[{shape}, {anchor}, {door}] control: the same composite declaring an early policy raised, so the"
        f" refusal above is not evidence that the stance is what it refuses: {run.raised(w.DECLARED_TWIN)}"
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
    # A question that raised (at any door: read off the side's own raise, not
    # off one door's shape of it), or a door that could not be reached, handed
    # out no reference at all; it is not a decision with a reference to compare.
    if w.refused_at_construction(shape):
        # P2 (c), a candidate: no question of this shape is answered, so it hands
        # out no reference to compare — provided each refusal is the named one.
        refusals = {side: run.raised(side).get(w.ONLY, "") for side in answered}
        assert all(w.raising_is_the_property(shape, w.ONLY, message) for message in refusals.values()), (
            f"[{shape}, {anchor}, {door}] a question of an undeclared composite was not refused by P2 (c)'s"
            f" construction refusal: {refusals}"
        )
        return
    references = {
        side: w.render(value, limit=10_000)
        for side, value in answered.items()
        if w.ONLY not in run.raised(side)
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
LISTED_SHAPES = w.LISTED_SHAPES

#: What each listed side must have raised, by type (Dave's Q12 as built, lane
#: ``378b-s020record`` PROPOSAL section 7, item 1). A class that does not affirm
#: ``never``, listed: refused where its resolver is built, in the deployment that
#: holds the subject and in the one that does not. The withheld subject under a
#: class that affirms ``never``: refused before anything is recorded —
#: ``NeverWithholdingContradicted`` on the paved road; for a composite, Q8's
#: late-withhold refusal runs first on this tree (``CompositeWithheldLate``).
LISTED_REFUSALS: dict[str, dict[str, str]] = {
    w.WITHHELD_LISTED_MAY: {shape: "WithholdingClassListedReadable" for shape in w.LISTED_SHAPES},
    w.NONEXISTENT_LISTED_MAY: {shape: "WithholdingClassListedReadable" for shape in w.LISTED_SHAPES},
    w.WITHHELD_READABLE: {
        w.SUBJECT_KEYED: "NeverWithholdingContradicted",
        w.COMPOSITE_SUBJECT_CHILD: "CompositeWithheldLate",
    },
}


def _owner_read_answered(run: w.Run, side: str, position: str = w.ONLY) -> bool:
    """Whether the owner's read of ``side``'s record by its reference was ANSWERED with the record."""
    reads = run.sides[side].read_check.get(position, {}).get("reads", {})
    if run.door == w.HTTP:
        return reads.get("owner:replay.resolutions", {}).get("status") == 200
    blob = reads.get("owner:blob", {})
    return any("blob_sha256" in part for part in blob.get("contents", []) if isinstance(part, dict))


@pytest.mark.parametrize("door", (w.HTTP, w.MCP))
@pytest.mark.parametrize("anchor", w.ANCHORS)
@pytest.mark.parametrize("shape", LISTED_SHAPES)
def test_a_withholding_class_listed_evidence_readable_does_not_reopen_the_record(
    runs: w.RunCache, shape: str, anchor: str, door: str
) -> None:
    """Dave, Q12: *"Default-deny owner read-back, with an explicit tenant class allowlist. Reject withholding classes."*

    PENDING until the allowlist exists under its documented name. Both
    configurations Q12 leaves a deployment, as built (lane ``378b-s020record``
    PROPOSAL section 7, item 1):

    * **A class that does not affirm ``never``, LISTED** — refused where its
      resolver is built, by name (:data:`LISTED_REFUSALS`), in the deployment
      that holds the subject AND in the one that does not: the listing is
      rejected alike, so nothing is answered, recorded or read back on either
      side. Equal by that NAMED refusal, which is the property here — as Q9's
      refusals are for the reused shapes — and never by an arbitrary exception.
    * **A class that affirms ``never``, LISTED, whose policy withholds the
      subject** — the withheld question is refused by name before anything is
      recorded, so no record of it exists to read back. The control: the
      nonexistent subject under the same listing is answered, and its owner
      reads its record back — the listing is live.

    The second arm leaves a response-level difference BY DESIGN: the withheld
    subject's question raises where the nonexistent subject's is answered.
    That is OWED ruling E2 (ii) (a class that declares it never withholds, and
    withholds, fails loudly, as a disclosed deployment obligation); Dave has
    not ruled it, and this cell passing does not rule it.
    """
    if not w.evidence_allowlist_exists():
        pytest.skip(f"pending API: {w.EVIDENCE_ALLOWLIST_FIELD} (ProductEntitlementPolicy)")
    run = runs.get(shape=shape, anchor=anchor, door=door)
    wrong: dict[str, Any] = {}
    for side, by_shape in LISTED_REFUSALS.items():
        expected = by_shape[shape]
        raised = run.raised(side).get(w.ONLY, "")
        if not raised.startswith(f"{expected}:"):
            wrong[side] = f"expected {expected}, observed: " + (raised or w.render(run.channel(side, w.RESPONSE)))
        record = run.channel(side, w.RECORD)
        if record != {"reference": None}:
            wrong[f"{side}:record"] = w.render(record)
    assert not wrong, (
        f"[{shape}, {anchor}, {door}] a listed class's record channel was not closed by the named refusal: {wrong}"
    )
    assert not run.raised(w.NONEXISTENT_READABLE) and _owner_read_answered(run, w.NONEXISTENT_READABLE), (
        f"[{shape}, {anchor}, {door}] control: the nonexistent subject under the listed class that affirms"
        " never was not answered and read back by its owner, so the refusals above are not evidence that"
        f" the listing is what they close: {w.render(run.channel(w.NONEXISTENT_READABLE, w.RECORD))}"
    )


#: Every shape whose readable serving deployment answers (Q9 refuses every question of ``reused_store``).
CALLER_REFERENCE_SHAPES = tuple(shape for shape in ALL_SHAPES if shape != w.REUSED_STORE)


@pytest.mark.parametrize("door", (w.HTTP, w.MCP))
@pytest.mark.parametrize("anchor", w.ANCHORS)
@pytest.mark.parametrize("shape", CALLER_REFERENCE_SHAPES)
def test_the_caller_visible_reference_resolves_through_the_governed_reads(
    runs: w.RunCache, shape: str, anchor: str, door: str
) -> None:
    """Dave, Q11: *"Use a caller-visible reference separate from the internal evidence address."*

    The marker this replaces waited for the reference's public name and read
    route. As built (lane ``378b-s020record`` PROPOSAL sections 7, item 3, and
    8) there is no new name: the caller-visible reference IS the ``replay_ref``
    / ``replay_reference`` each door hands out — a URI whose name and version
    are the record's content address, which reflects nothing the answer read —
    and its read route is the governed evidence reads. Held here, on the
    deployment whose tenant lists the class and whose class affirms ``never``
    (so its owner may read the record): the record cells were presented with
    exactly the reference the door handed out; the owner's read BY THAT URI
    (HTTP ``/replay/resolutions``; MCP: the URI's resolution, then the blob at
    the address it answers) answered; and the bytes it returned hash to the
    URI's version, which is its name.
    """
    if not w.evidence_allowlist_exists():
        pytest.skip(f"pending API: {w.EVIDENCE_ALLOWLIST_FIELD} (ProductEntitlementPolicy)")
    _require(shape)
    run = runs.get(shape=shape, anchor=anchor, door=door)
    position = "first" if shape in w.REUSED_SHAPES else w.ONLY
    raised = run.raised(w.SERVED_READABLE).get(position)
    assert not raised, f"[{shape}, {anchor}, {door}] not evidence: the readable serving question raised: {raised}"
    check = run.sides[w.SERVED_READABLE].read_check.get(position, {})
    handed_out = check.get("handed_out")
    assert isinstance(handed_out, str) and handed_out.startswith("ccf-artifact://"), (
        f"[{shape}, {anchor}, {door}] the door handed out no reference: {w.render(check)}"
    )
    assert check.get("presented") == handed_out, (
        f"[{shape}, {anchor}, {door}] the record cells read {check.get('presented')!r}, not the reference"
        f" the door handed out, {handed_out!r}"
    )
    parsed = w.parse_artifact_uri(handed_out)
    assert parsed.name == parsed.artifact_version, f"[{shape}, {anchor}, {door}] name is not version: {handed_out}"
    reads = check.get("reads", {})
    if door == w.HTTP:
        by_uri = reads.get("owner:replay.resolutions", {})
        assert by_uri.get("status") == 200, f"[{shape}, {anchor}, {door}] the owner's read by URI: {by_uri}"
        assert by_uri.get("sha256") == parsed.artifact_version, (
            f"[{shape}, {anchor}, {door}] the owner's read by URI returned bytes that hash to"
            f" {by_uri.get('sha256')}, not the reference's version {parsed.artifact_version}"
        )
        return
    resolution = reads.get("owner:resolution", {})
    answered = [part.get("text") for part in resolution.get("contents", []) if isinstance(part, dict)]
    assert any(
        isinstance(text, dict) and text.get("found") is True and text.get("content_address") == parsed.artifact_version
        for text in answered
    ), f"[{shape}, {anchor}, {door}] the owner's resolution of the URI: {w.render(resolution)}"
    blob = reads.get("owner:blob", {})
    digests = [part.get("blob_sha256") for part in blob.get("contents", []) if isinstance(part, dict)]
    assert parsed.artifact_version in digests, (
        f"[{shape}, {anchor}, {door}] the owner's blob read at the resolved address returned bytes hashing to"
        f" {digests}, not the reference's version {parsed.artifact_version}"
    )


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
    if channel == w.REFERENCE:
        # Q11, as in the standing instrument: the reference channel is
        # instrumented by Q11's properties, never by a difference.
        problems = w.reference_properties(run)
        assert not problems, (
            f"same-deployment reference instrument [{shape}, {anchor}, {door}]: Dave's Q11 properties do"
            f" not hold: {problems}"
        )
        return
    left_side, right_side, floor_a, floor_b = w.same_instrument_sides(channel, run)
    vacuous = _vacuous(run, left_side, right_side, either=True)
    assert not vacuous, (
        f"same-deployment instrument not evidence [{shape}, {anchor}, {door}, {channel}]: a side"
        f" RAISED instead of answering, so a difference it shows is the exception's: {vacuous}"
    )
    same = w.SAME_DEPLOYMENT
    left = run.channel(left_side, channel, comparison=same)
    right = run.channel(right_side, channel, comparison=same)
    floor = w.diff_paths(
        run.channel(floor_a, channel, comparison=same),
        run.channel(floor_b, channel, comparison=same),
    )
    seen = w.diff_paths(left, right) - floor
    assert seen, (
        f"same-deployment instrument broken [{shape}, {anchor}, {door}, {channel}]: {left_side} and"
        f" {right_side} are indistinguishable on this channel, so a PASS of its same-deployment"
        f" comparison would prove nothing\n  {left_side}: {w.render(left)}\n  {right_side}: {w.render(right)}"
    )
