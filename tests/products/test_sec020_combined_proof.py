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
as refused. Where P2's option (c) is on the tree (``D-IMPL-378``, ruled by Dave
on 2026-10-08 at 12:29 MST), the two late-composite shapes declare no
withholding stance and every question of theirs is its construction refusal,
``CompositeNeedsAWithholdingStance`` (``sec020_worlds.CONSTRUCTION_REFUSALS``),
held the same way, with each instrument set against the same composite
declaring a stance (``sec020_worlds.DECLARED_TWIN``). Where ruling P6 (a) is on
the tree (``D-IMPL-378``, ruled by Dave on 2026-10-08 at 16:40 MST: *"Extend
CT-A with the working declared-population twin"*), every question of the
``population`` shape — a population read left in the subject-keyed phase under
a late withhold — ends in ``PopulationReadInSubjectKeyedPhase``, decided by the
P6 probe and never by the subject; that refusal counts as the property its
cells hold only when every probed side observed it with one message AND the
declared-population twin (the same source, its read declared through
``open_product(population=...)``: the ``population_declared`` world) answered
both its questions (``sec020_worlds.p6_refused``;
``test_a_population_read_in_the_subject_keyed_phase_is_refused_for_every_question``),
and each of the shape's instruments is then set against that twin answering.
Its cells stay in the gate, unretired and unmarked.

**Nor on a noise floor whose copy failed** (Dave, 2026-10-09 06:06 MST, ``D-IMPL-378``: *"prove that the
control successfully answered before using it to excuse differences"*; approved at 06:21 MST: *"A failed spare
answer cannot excuse differences. Apply the check to the gate and limitation measurements"*). A noise floor is read
off a second copy of the nonexistent side. Where that copy RAISED, other than the refusal held as the property and
raised by the side it copies as well, the floor compares an exception with an answer, differs at every path, and
would excuse every difference. Every comparison checks the copy first (``_compare``): a gate or never-class cell
fails by name, ``FloorCopyDidNotAnswer``, and a limitation measurement reports the cell under its own outcome,
``floor copy raised``, neither distinguishable nor indistinguishable, because nothing was measured.

**X17 (a): the pin channel** (Dave, 2026-10-09 06:06 MST, confirmed 06:21 MST, ``D-IMPL-378``: *"Cover versioned
resolution and write-then-read in the closure gate"*).
``test_a_pin_filed_in_one_deployment_reads_alike_in_both[<shape>-<anchor>-<surface>]`` reads, as the asker, every
executed-query pin filed in only one of the counterfactual's two deployments, in both, at every surface the asker can
read it at, write-then-read included. Its instrument is ``test_the_pin_instrument_sees_a_difference``, and its
population is reported every run by ``test_the_pin_channel_census_is_measured_and_reported``. An outsider recomputing
a pin's address without the record is unreproduced, and that does not excuse the channel.

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

**A separately reported limitation, not a removal** (Dave's E3, 2026-10-08
12:29 MST, ``D-IMPL-378``: *"yes to the previously ruled same-deployment
comparison for population sources. Retain the retired two-deployment cells as a
separately reported limitation."*). The 88 retired cells still EXECUTE, every
run of this module, through the same comparison and the same "not evidence"
rule as the gate's cells, in
:func:`test_d1a_limitation_the_retired_two_deployment_cells_are_measured_not_gated`,
which prints how many are distinguishable in its own block of the run's output
(``SEC-020 D1 (a) LIMITATION``) and records it in the JUnit record
(``d1a_limitation``). Their outcome is reported and never asserted: they do not
count toward the gate's pass, and that test fails only if a retired cell could
not be measured at all.

**Ruling P6 (a)'s counterexample, reported the same way** (Dave, 2026-10-08
16:40 MST, ``D-IMPL-378``: *"retain the counterexample where a source treats the
probe identifier differently"*). The ``population`` world with its source
swapped for one that answers nothing for the probe identifier (exactly, or by
its shape) and the whole population for every other identifier passes the
probe; its same-deployment cells EXECUTE every run, through the same
comparison and the same "not evidence" rule as a gate cell, in
:func:`test_p6_limitation_a_source_that_recognizes_the_probe_is_measured_not_gated`,
which prints them in their own block (``SEC-020 P6 PROBE LIMITATION``) and
records them in the JUnit record (``p6_probe_limitation``). They are not gate
cells, never count toward the gate's pass, and the test fails only if the
counterexample was not constructed or a cell could not be measured.

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

Dave ruled E1 (a) on 2026-10-08 12:29 MST (``D-IMPL-378``), verbatim: *"Approve
random per-answer issuance and the named conformance amendments. Preserve
record content-address integrity. Random references must have indistinguishable
distributions; equality is no longer the criterion."* So a REFERENCE is judged
by distribution, never by equality (lane ``378e-s020``):

* **Per cell** (:func:`_compare`), wherever both sides hold a reference at one
  path — the answer's reference, and the reference a governed read's own
  refusal is recorded under — the two must have the same FORM
  (``sec020_worlds.reference_form``: scheme, tenant, class, each identifying
  segment's length and alphabet, name and version one identity), and the
  nonexistent side's two copies must differ there too (a reference fixed on one
  side is not a draw from any distribution). The noise floor no longer excuses
  a reference's VALUE: these two rules replace it. A difference in KIND
  (missing against present, a reference against other text) stays a failure
  (CT-C (a)).
* **Pooled per comparison**
  (:func:`test_withheld_and_nonexistent_references_are_drawn_from_one_distribution`):
  the withheld side's distinct reference tokens and the nonexistent side's,
  over every cell of the comparison, pass a two-sample Kolmogorov-Smirnov test
  at the stated level, with the stated minimum sample per side.

These adaptations decided nothing Dave had not ruled: E1 and E2 were OWED when
they were made (``records/2026-10-08-d-impl-378-ci-lane/OWED-RULINGS.md``);
Dave ruled them on 2026-10-08 at 12:29 MST.

SEC-020 is OPEN: Dave approved E1 (a), E2 (i) and (iii), P2 (c), CT-A (a) and
CT-C (a), and did not approve closure; CT-B is not approved, so the 22
undeclared-population cells stay in the gate — judged, since his ruling P6 (a)
of 2026-10-08 16:40 MST, by CT-A extended to the P6 refusal (above). He did not
approve closure on that probe alone: *"Do not declare closure based on this
probe alone."*

E2 (ii): a class that affirms ``never`` and withholds anyway (Dave, 2026-10-08 12:29 MST)
------------------------------------------------------------------------------------------
Ruled a measured oracle, "REJECTED as disclosure-only": the withheld subject's
question raising where a nonexistent subject's is answered tells the two apart.
``test_a_withheld_subject_under_a_never_class_is_indistinguishable[<comparison>-<configuration>-<anchor>-<door>-<channel>]``
judges it by this module's own rules, one ``configuration`` per way the class
and its projection can meet (``sec020_worlds.NEVER_CONFIGURATIONS``), with an
instrument per channel (``test_the_never_instrument_sees_a_difference``). Its
cells stay in the gate, unmarked, until no configuration leaves the two
distinguishable.

Dave's option (d), 2026-10-08 16:40 MST (``D-IMPL-378``), verbatim: *"Require a
positive declaration, default silence to refusal, and explicitly limit the
trusted-code assumption to deployment code callers cannot influence. Keep the
false-declaration counterexample visible."* A class affirming ``never`` is now
built only over a plan factory that positively declares it never withholds, so
every configuration here — its factory declaring that it withholds, or declaring
nothing — is refused where its resolver is built, on every side. Under CT-A (a)
a cell holds that refusal as the property only when the withheld, nonexistent
and noise-floor sides ALL observed the SAME construction refusal, by name
(``sec020_worlds.NEVER_CONSTRUCTION_REFUSALS``: ``NeverWithholdingProjectionCanWithhold``,
or since (d) ``NeverWithholdingNeedsAPositiveDeclaration``), and the declared
twin — the policy off, positively declaring that it never withholds — answers.

**A separately reported limitation, not a gate cell** (the same (d), *"Keep the
false-declaration counterexample visible"*). A plan factory that positively
declares it never withholds while its projection withholds is built: the
declaration is trusted deployment code, an assumption (d) limits to code no
caller can influence. Its configurations
(``sec020_worlds.NEVER_FALSE_DECLARATION_CONFIGURATIONS``) generate no gate
cell; every run executes all of their cells through the gate's own rules in
:func:`test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated`,
which prints them in their own block (``SEC-020 E2 (ii) FALSE-DECLARATION
LIMITATION``) and records them in the JUnit record
(``e2ii_false_declaration_limitation``). They never count as passing evidence,
and no mark hides them.

The listed-class cell below holds only the record channel of a listed
``never`` class whose policy withholds; under (d) that class is refused where
its resolver is built, so nothing is recorded to read back. It is not evidence
of indistinguishability.

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import json
import logging
import pathlib
from collections.abc import Callable, Iterator
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
    """Differing paths (noise floor removed), the floor itself, and the two values.

    Dave's E1 (a) (``D-IMPL-378``; the module docstring): at a path where both
    sides hold a REFERENCE, equality is no longer the criterion and the noise
    floor no longer excuses the value. Such a path is counted when the two
    references differ in form (``sec020_worlds.reference_form``), or when the
    nonexistent side's two copies hold one reference there (a value fixed on
    one side is not drawn from any distribution); the two sides' values are
    judged together, over the whole comparison, by
    :func:`test_withheld_and_nonexistent_references_are_drawn_from_one_distribution`.
    Every other path is judged exactly as before.

    **The floor's copy must have answered** (Dave, 2026-10-09 06:06/06:21 MST, ``D-IMPL-378``: *"A failed
    spare answer cannot excuse differences"*). Before anything is judged, :func:`_require_the_floor_copy_answered`
    fails the cell by name, :class:`FloorCopyDidNotAnswer`, where the floor's copy raised other than as the refusal
    held as the property together with the side it copies (:func:`_floor_copy_did_not_answer`).
    """
    # Dave, 2026-10-09: before the floor excuses anything, its copy must have answered (BLD-1, G-FLOOR-COPY).
    _require_the_floor_copy_answered(run, comparison)
    withheld_side, nonexistent_side, floor_side = w.PAIRS[comparison]
    withheld = run.channel(withheld_side, channel, comparison=comparison)
    nonexistent = run.channel(nonexistent_side, channel, comparison=comparison)
    floor = w.diff_paths(nonexistent, run.channel(floor_side, channel, comparison=comparison))
    differing = w.diff_paths(withheld, nonexistent)
    # The floor excuses a difference in VALUE, never in KIND (``sec020_worlds.kind_diff_paths``):
    # under Q11 two nonexistent copies differ at every reference path, which must not
    # excuse a withheld side handed no reference where the nonexistent side was handed one.
    counted = (differing - floor) | (differing & floor & w.kind_diff_paths(withheld, nonexistent))
    # E1 (a): a reference on both sides is judged by FORM here, and by distribution
    # in the pooled test; never by the floor's excusal of its value.
    on_withheld = w.reference_leaves(withheld, channel=channel)
    on_nonexistent = w.reference_leaves(nonexistent, channel=channel)
    references = differing & set(on_withheld) & set(on_nonexistent)
    counted |= {path for path in references if path not in floor}
    counted |= {
        path for path in references
        if w.reference_form(on_withheld[path]) != w.reference_form(on_nonexistent[path])
    }
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
            if position in r
            and not w.raising_is_the_property(run.shape, position, r[position])
            and not w.p6_refusal_is_the_property(run, position, r[position])
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


def _reference_samples(
    runs: w.RunCache, comparison: str
) -> tuple[dict[str, set[str]], dict[str, list[str]], list[str]]:
    """The withheld and the nonexistent side's distinct reference tokens and issuances, over one comparison's cells.

    References are read through the same channels and the same comparison the
    cells read, at every reference leaf (``sec020_worlds.reference_leaves``);
    distinct tokens only, since one answer's reference appears at several paths.
    Issuances are those of the records the sides' answers name, read from each
    deployment's own store as an auditor would (``Observation.reference_facts``),
    one per answer. Returns ``({"withheld", "nonexistent", "withheld-issuance",
    "nonexistent-issuance": ...}, issuances that repeat, leaves not of the
    reference form)``.
    """
    withheld_side, nonexistent_side, _ = w.PAIRS[comparison]
    labels = {withheld_side: "withheld", nonexistent_side: "nonexistent"}
    samples: dict[str, set[str]] = {name: set() for label in labels.values()
                                     for name in (label, f"{label}-issuance")}
    seen: dict[str, list[str]] = {}
    malformed: list[str] = []
    measured: set[tuple[str, str, str]] = set()
    for param in _cells():
        cell_comparison, shape, anchor, door, channel = param.values
        if cell_comparison != comparison:
            continue
        if shape in w.PENDING_SHAPES and not w.PENDING_SHAPES[shape][1]():
            continue
        run = runs.get(shape=shape, anchor=anchor, door=door)
        for side, label in labels.items():
            for path, leaf in w.reference_leaves(run.channel(side, channel, comparison=comparison),
                                                 channel=channel).items():
                token = w.reference_token(leaf)
                if w.REFERENCE_TOKEN.match(token):
                    samples[label].add(token)
                else:
                    malformed.append(f"{param.id} {side} {path}: {leaf!r}")
        for side, label in labels.items():
            key = (f"{shape}-{anchor}-{door}", side, label)
            if key in measured:
                continue
            measured.add(key)
            for reference, facts in run.sides[side].reference_facts.items():
                issuance = facts.get("issuance")
                if issuance is None:
                    continue
                samples[f"{label}-issuance"].add(issuance)
                seen.setdefault(issuance, []).append(f"{key[0]} {side} {reference}")
    repeated = {issuance: where for issuance, where in seen.items() if len(where) > 1}
    return samples, repeated, malformed


@pytest.mark.parametrize("comparison", w.COMPARISONS)
def test_withheld_and_nonexistent_references_are_drawn_from_one_distribution(
    runs: w.RunCache, comparison: str, record_testsuite_property: Callable[[str, object], None]
) -> None:
    """Dave's E1 (a): *"Random references must have indistinguishable distributions."*

    **The test.** Every distinct reference token the withheld side was handed,
    over every cell of this comparison in the gate, against every one the
    nonexistent side was handed: each token is read as the fraction its leading
    52 bits make of [0, 1) (``sec020_worlds.token_position``), and a two-sample
    Kolmogorov-Smirnov test at ``sec020_worlds.REFERENCE_DISTRIBUTION_ALPHA``
    (1e-4) must not reject that the two were drawn from one distribution. At
    least ``sec020_worlds.REFERENCE_DISTRIBUTION_MIN_SAMPLES`` (50) distinct
    tokens per side, or the run is not evidence; every token must be of the
    reference form (64 lowercase hexadecimal characters). The same test holds
    the two sides' per-answer ISSUANCES (read from each record as an auditor
    would; at least ``sec020_worlds.ISSUANCE_DISTRIBUTION_MIN_SAMPLES`` a
    side), every answer's record must carry one, and no two answers' records may
    share one: a reference is a content hash, spread over the space whatever it
    hashes, so a withheld answer issued a constant would hide from the
    reference test and not from this one.

    **Its power, stated honestly.** The critical gap is
    ``sqrt(-ln(alpha / 2) / 2) * sqrt((n + m) / (n * m))``: 0.445 at 50 tokens a
    side, 0.18 at 300. So it catches a side whose references are confined to a
    part of the space — a constant or repeated reference, a fixed leading digit,
    references drawn from half the space at the smaller sizes — and it does NOT
    catch a slight bias in a few bits, or a reference that is a deterministic
    but uniform-looking function of what the answer read (a content hash of the
    read is spread over the space exactly as a random token is). That last case
    is held elsewhere: the reference instrument requires two copies of one
    deployment asked one question to be handed different references
    (``sec020_worlds.reference_properties``, property 1), and :func:`_compare`
    counts a reference the nonexistent side's two copies agree on. A false
    alarm — red while both sides ARE drawn from one distribution — happens in
    about one run in 10,000, and cannot be reproduced on demand, because the
    references are fresh randomness on every run.
    """
    samples, repeated, malformed = _reference_samples(runs, comparison)
    assert not malformed, (
        f"[{comparison}] references not of the reference form, so not samples: {malformed[:10]}"
    )
    unissued = sorted(token for label in ("withheld-issuance", "nonexistent-issuance")
                      for token in samples[label] if not w.REFERENCE_TOKEN.match(token))
    assert not unissued, f"[{comparison}] an answer's record carries no per-answer issuance: {unissued[:5]}"
    assert not repeated, f"[{comparison}] two answers' records share one issuance: {dict(list(repeated.items())[:5])}"
    measured: dict[str, dict[str, Any]] = {}
    for what, minimum in (
        ("", w.REFERENCE_DISTRIBUTION_MIN_SAMPLES),
        ("-issuance", w.ISSUANCE_DISTRIBUTION_MIN_SAMPLES),
    ):
        withheld, nonexistent = samples[f"withheld{what}"], samples[f"nonexistent{what}"]
        assert len(withheld) >= minimum and len(nonexistent) >= minimum, (
            f"[{comparison}{what}] not evidence: {len(withheld)} withheld and {len(nonexistent)}"
            f" nonexistent distinct tokens, fewer than {minimum} a side"
        )
        statistic = w.ks_two_sample(
            (w.token_position(token) for token in withheld),
            (w.token_position(token) for token in nonexistent),
        )
        critical = w.ks_critical(len(withheld), len(nonexistent), w.REFERENCE_DISTRIBUTION_ALPHA)
        measured[what or "-reference"] = {
            "withheld": len(withheld), "nonexistent": len(nonexistent),
            "statistic": round(statistic, 6), "critical": round(critical, 6),
        }
    # The measurement, in the run's own JUnit record, whichever way it falls.
    record_testsuite_property(f"reference_distribution_{comparison}", json.dumps({
        "comparison": comparison, "alpha": w.REFERENCE_DISTRIBUTION_ALPHA, **measured,
    }, sort_keys=True))
    rejected = {what: found for what, found in measured.items() if found["statistic"] > found["critical"]}
    assert not rejected, (
        f"SEC-020 [{comparison}]: the withheld side's tokens are distinguishable in distribution from the"
        f" nonexistent side's (Kolmogorov-Smirnov statistic above its critical value at alpha"
        f" {w.REFERENCE_DISTRIBUTION_ALPHA}): {rejected}"
    )


def test_the_reference_distribution_test_sees_a_planted_difference() -> None:
    """The pooled test's instrument: confined references are rejected, fresh ones are not.

    Planted, not observed: a side whose tokens all start with one hexadecimal
    digit (confined to a sixteenth of the space) against fresh tokens, at the
    smallest sample the pooled test accepts, must be rejected; two sets of fresh
    tokens must not be (a false alarm here is the same one-in-10,000 chance).
    """
    import secrets  # noqa: PLC0415

    minimum = w.REFERENCE_DISTRIBUTION_MIN_SAMPLES
    fresh = [secrets.token_hex(32) for _ in range(minimum)]
    other = [secrets.token_hex(32) for _ in range(minimum)]
    confined = ["0" + secrets.token_hex(32)[1:] for _ in range(minimum)]
    critical = w.ks_critical(minimum, minimum, w.REFERENCE_DISTRIBUTION_ALPHA)
    positions = {name: [w.token_position(token) for token in tokens]
                 for name, tokens in (("fresh", fresh), ("other", other), ("confined", confined))}
    assert w.ks_two_sample(positions["confined"], positions["fresh"]) > critical
    assert w.ks_two_sample(positions["other"], positions["fresh"]) <= critical
    assert all(w.REFERENCE_TOKEN.match(token) for token in fresh + other + confined)


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
    if channel == w.REFERENCE and shape != w.REUSED_STORE and w.DECLARED_TWIN not in run.sides and not w.p6_refused(run):
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
    """``D-IMPL-378`` P2, option (c), which Dave ruled on 2026-10-08 at 12:29 MST.

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


#: The shapes ruling P6 (a) refuses every question of, on this tree (empty where the refusal does not exist).
P6_REFUSED_SHAPES = tuple(shape for shape in w.P6_REFUSED_SHAPES if w.probe_refusal_exists())


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
@pytest.mark.parametrize("shape", P6_REFUSED_SHAPES)
def test_a_population_read_in_the_subject_keyed_phase_is_refused_for_every_question(
    runs: w.RunCache, shape: str, anchor: str, door: str
) -> None:
    """``D-IMPL-378`` ruling P6 (a) — CT-A extended, which Dave ruled on 2026-10-08 at 16:40 MST.

    Dave, verbatim: *"Extend CT-A with the working declared-population twin."*
    A class that may withhold, declares no early policy and reads its
    population inside the subject-keyed phase is refused, every question,
    ``PopulationReadInSubjectKeyedPhase``, decided by the probe and never by
    the subject: every probed side of every deployment of this shape — the
    source holding the subject or not, the policy on or off, the withheld
    subject or an identifier nothing holds — observes that ONE refusal, by
    name, with one message, at every door (read by type behind HTTP and MCP
    off the resolver each door was handed). This is the property the shape's
    cells are held on (``sec020_worlds.p6_refused``). The control: the same
    source with its read declared as the population phase
    (``open_product(population=...)``, the ``population_declared`` world),
    withholding the same subject, ANSWERS both questions — so the refusal is
    the undeclared read's, not a broken builder's. Not closure: a source that
    recognizes the probe is not detected.
    """
    run = runs.get(shape=shape, anchor=anchor, door=door)
    refusals = {side: run.raised(side).get(w.ONLY, "") for side in w.P6_PROBED_SIDES}
    wrong = {
        side: refusal or w.render(run.channel(side, w.RESPONSE))
        for side, refusal in refusals.items()
        if not refusal.startswith(f"{w.P6_REFUSAL}:")
    }
    assert not wrong, f"[{shape}, {anchor}, {door}] not refused by {w.P6_REFUSAL}: {wrong}"
    assert len(set(refusals.values())) == 1, (
        f"[{shape}, {anchor}, {door}] the refusal must be worded once, whatever was asked: {sorted(set(refusals.values()))}"
    )
    for twin in (w.POPULATION_TWIN, w.POPULATION_TWIN_NEVER_HELD):
        assert not run.raised(twin), (
            f"[{shape}, {anchor}, {door}] control: the same source with its population read declared raised"
            f" ({twin}), so the refusal above is not evidence that the undeclared read is what it refuses:"
            f" {run.raised(twin)}"
        )
    assert w.p6_refused(run), f"[{shape}, {anchor}, {door}] CT-A extended does not hold for this run"


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
        # P2 (c) (`D-IMPL-378`, ruled 2026-10-08 12:29 MST): no question of this
        # shape is answered, so it hands out no reference to compare — provided
        # each refusal is the named one.
        refusals = {side: run.raised(side).get(w.ONLY, "") for side in answered}
        assert all(w.raising_is_the_property(shape, w.ONLY, message) for message in refusals.values()), (
            f"[{shape}, {anchor}, {door}] a question of an undeclared composite was not refused by P2 (c)'s"
            f" construction refusal: {refusals}"
        )
        return
    if shape in w.P6_REFUSED_SHAPES and w.probe_refusal_exists():
        # CT-A extended to ruling P6 (a) (`D-IMPL-378`, Dave 2026-10-08 16:40 MST):
        # no question of this shape is answered, so it hands out no reference
        # to compare — provided each refusal is P6's, held as the property.
        refusals = {side: run.raised(side).get(w.ONLY, "") for side in answered}
        assert all(w.p6_refusal_is_the_property(run, w.ONLY, message) for message in refusals.values()), (
            f"[{shape}, {anchor}, {door}] a question of a population read left in the subject-keyed phase was"
            f" not refused by ruling P6 (a)'s refusal held as the property (CT-A extended): {refusals}"
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
#: class that affirms ``never`` and whose policy withholds it: since Dave's
#: E2 (ii) (d) (2026-10-08 16:40 MST) that deployment's plan factory does not
#: positively declare that it never withholds — its policy is on, and it says
#: so — so the class is refused where its resolver is built, before anything is
#: read or recorded, by ``sec020_worlds.NEVER_DECLARATION_REFUSAL``; for a
#: composite too. Until (d) this arm expected the runtime DEFENSE,
#: ``NeverWithholdingContradicted``; under (d) the defense is reached only through
#: a FALSE positive declaration — trusted deployment code — which this module
#: never counts as passing evidence and reports outside the gate instead
#: (:func:`test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated`,
#: whose record-channel cells measure exactly that case).
LISTED_REFUSALS: dict[str, dict[str, str]] = {
    w.WITHHELD_LISTED_MAY: {shape: "WithholdingClassListedReadable" for shape in w.LISTED_SHAPES},
    w.NONEXISTENT_LISTED_MAY: {shape: "WithholdingClassListedReadable" for shape in w.LISTED_SHAPES},
    w.WITHHELD_READABLE: {shape: w.NEVER_DECLARATION_REFUSAL for shape in w.LISTED_SHAPES},
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
      subject** — since Dave's E2 (ii) (d) its plan factory, whose policy is on,
      does not positively declare that it never withholds, so the class is
      refused where its resolver is built, by name, before anything is read or
      recorded; no record of the question exists to read back. The control:
      the nonexistent subject under the same listing — the policy off, truly
      declaring — is answered, and its owner reads its record back — the
      listing is live.

    The second arm holds the RECORD CHANNEL only. Until (d) it expected the
    runtime defense, raised for the withheld subject alone — the oracle Dave
    ruled (E2 (ii), 2026-10-08 12:29 MST, "REJECTED as disclosure-only"). That
    defense is now reached only through a FALSE positive declaration, the
    residual (d) leaves to trusted deployment code; it is measured, every run,
    outside the gate by
    :func:`test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated`,
    and is never counted here.
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


def test_d1a_limitation_the_retired_two_deployment_cells_are_measured_not_gated(
    runs: w.RunCache, record_testsuite_property: Callable[[str, object], None], capsys: Any
) -> None:
    """Dave's E3: the 88 retired two-deployment cells, executed and reported as a limitation, never gated.

    Dave, 2026-10-08 12:29 MST (``D-IMPL-378``), E3, verbatim: *"yes to the
    previously ruled same-deployment comparison for population sources.
    Retain the retired two-deployment cells as a separately reported
    limitation."* Every cell in :data:`RETIRED_D1A` is run through exactly what
    a gate cell runs — :func:`_vacuous` and then :func:`_compare` — and its
    outcome is classified: ``distinguishable`` (the cell would fail in the
    gate), ``indistinguishable``, or ``not evidence`` (both sides raised).

    **What this asserts, and what it does not.** It asserts that every retired
    cell was MEASURED, and nothing about the outcome: the cells are a reported
    limitation, so how many are distinguishable never moves the gate. The
    measurement is printed to the run's own output, in its own block headed
    ``SEC-020 D1 (a) LIMITATION`` (written past the output capture, so it shows
    in every run), and recorded in the JUnit record as ``d1a_limitation``. A
    cell that cannot be measured — its run fails to build, a channel is missing
    — fails this test, because an unmeasured limitation is not reported.

    **A floor copy that did not answer** (Dave, 2026-10-09, ``D-IMPL-378``: *"A failed spare answer cannot excuse
    differences. Apply the check to the gate and limitation measurements"*). A cell whose noise floor's copy raised
    (:func:`_floor_copy_did_not_answer`) is classified :data:`FLOOR_COPY_OUTCOME`, by name, with what the copy
    raised, and is never judged off that floor: it was not measured, so it is reported as neither distinguishable
    nor indistinguishable, in the same block and the same JUnit record.
    """
    outcomes: dict[str, dict[str, Any]] = {}
    for cell in RETIRED_D1A:
        comparison, shape, anchor, door, channel = cell.split("-")
        run = runs.get(shape=shape, anchor=anchor, door=door)
        withheld_side, nonexistent_side, _ = w.PAIRS[comparison]
        vacuous = _vacuous(run, withheld_side, nonexistent_side)
        if vacuous:
            outcomes[cell] = {"outcome": "not evidence", "raised": sorted(vacuous)}
            continue
        unanswered = _floor_copy_did_not_answer(run, comparison)
        if unanswered:
            outcomes[cell] = {"outcome": FLOOR_COPY_OUTCOME, "raised": sorted(unanswered)}
            continue
        differing, floor, _, _ = _compare(run, comparison=comparison, channel=channel)
        outcomes[cell] = (
            {"outcome": "distinguishable", "at": sorted(differing)}
            if differing
            else {"outcome": "indistinguishable"}
        )
    assert sorted(outcomes) == sorted(RETIRED_D1A), "a retired cell was not measured"
    counts: dict[str, int] = {}
    for found in outcomes.values():
        counts[found["outcome"]] = counts.get(found["outcome"], 0) + 1
    record_testsuite_property("d1a_limitation", json.dumps(
        {"cells": len(outcomes), "counts": counts, "outcomes": outcomes}, sort_keys=True
    ))
    lines = [
        "",
        "=" * 30 + " SEC-020 D1 (a) LIMITATION (reported, NOT in the gate) " + "=" * 30,
        f"the {len(outcomes)} two-deployment cells D1 (a) retired, measured on this run:"
        f" {json.dumps(counts, sort_keys=True)}",
        *(f"  {cell}: {found['outcome']}" + (f" at {found['at']}" if "at" in found else "")
          for cell, found in sorted(outcomes.items())),
        "=" * 115,
    ]
    with capsys.disabled():
        print("\n".join(lines))


# =============================================================================
# Ruling P6 (a)'s retained counterexample: a source that recognizes the probe
# =============================================================================
#
# Dave, 2026-10-08 16:40 MST (``D-IMPL-378``), item 2, verbatim: "Do not declare
# closure based on this probe alone: prove it runs before real-subject
# acquisition, and retain the counterexample where a source treats the probe
# identifier differently." The reviewer's framing he relayed: "P6 is still the
# main risk: a source can recognize the probe and behave differently." Measured
# every run, reported in its own block of the output as E3's limitation is;
# never a gate cell.


def _p6_limitation_cells() -> list[tuple[str, str, str, str]]:
    """Every (recognition, anchor, door, channel) the P6 probe limitation measures, same-deployment."""
    return [
        (recognition, anchor, door, channel)
        for recognition in w.PROBE_RECOGNITIONS
        for anchor in w.ANCHORS
        for door in w.DOORS
        for channel in w.channels_for(comparison=w.SAME_DEPLOYMENT, shape=w.POPULATION, door=door)
    ]


def test_p6_limitation_a_source_that_recognizes_the_probe_is_measured_not_gated(
    tmp_path_factory: pytest.TempPathFactory, record_testsuite_property: Callable[[str, object], None], capsys: Any
) -> None:
    """Ruling P6 (a)'s counterexample, executed and reported as a limitation, never gated.

    SEC-020's ``population`` world with its source swapped for one that
    answers NOTHING for the probe identifier — recognized exactly, or by its
    shape — and the whole population for every other identifier
    (``sec020_worlds.ProbeRecognizingPopulationSource``, built by
    ``sec020_worlds.probe_recognizing_run``): the probe admits it, and the
    withheld subject and an identifier nothing holds are compared exactly as a
    gate cell compares them — :func:`_vacuous`, then :func:`_compare` — in the
    same-deployment comparison D1 (a) makes govern population sources, and
    classified ``distinguishable``, ``indistinguishable`` or ``not evidence``.

    **What this asserts, and what it does not.** It asserts that the
    counterexample was CONSTRUCTED — every question handed the source the probe
    identifier first, and the source answered nothing for it — and that every
    cell was MEASURED; nothing about the outcome. The measurement is printed in
    its own block of the run's output, headed ``SEC-020 P6 PROBE LIMITATION``
    (written past the output capture, so it shows in every run), and recorded
    in the JUnit record as ``p6_probe_limitation``. Its cells are not gate
    cells and never count toward the gate's pass;
    ``tests/products/test_sec020_p6_probe_recognizing_source_counterexample.py``
    is where the counterexample is held to still hold.

    **A floor copy that did not answer** (Dave, 2026-10-09, ``D-IMPL-378``: *"A failed spare answer cannot excuse
    differences. Apply the check to the gate and limitation measurements"*). A cell whose noise floor's copy raised
    (:func:`_floor_copy_did_not_answer`) is classified :data:`FLOOR_COPY_OUTCOME`, by name, with what the copy
    raised, and is never judged off that floor: it was not measured, so it is reported as neither distinguishable
    nor indistinguishable, in the same block and the same JUnit record.
    """
    levels = {name: logging.getLogger(name).level for name in _QUIETED_LOGGERS}
    for name in _QUIETED_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    probe = w.probe_identifier()
    outcomes: dict[str, dict[str, Any]] = {}
    unconstructed: dict[str, Any] = {}
    try:
        for recognition in w.PROBE_RECOGNITIONS:
            for anchor in w.ANCHORS:
                for door in w.DOORS:
                    key = f"{recognition}-{anchor}-{door}"
                    run = w.probe_recognizing_run(
                        pathlib.Path(tmp_path_factory.mktemp(f"p6-probe-limitation-{key}")),
                        recognition=recognition, anchor=anchor, door=door,
                    )
                    asked, nothing = run.notes["asked"], run.notes["answered_nothing_for"]
                    if nothing != [probe] * 3 or asked[::2] != [probe] * 3:
                        unconstructed[key] = run.notes
                    for channel in w.channels_for(comparison=w.SAME_DEPLOYMENT, shape=w.POPULATION, door=door):
                        cell = f"{w.SAME_DEPLOYMENT}-{key}-{channel}"
                        vacuous = _vacuous(run, w.CF_WITHHELD, w.SAME_NONEXISTENT)
                        if vacuous:
                            outcomes[cell] = {"outcome": "not evidence", "raised": sorted(vacuous)}
                            continue
                        unanswered = _floor_copy_did_not_answer(run, w.SAME_DEPLOYMENT)
                        if unanswered:
                            outcomes[cell] = {"outcome": FLOOR_COPY_OUTCOME, "raised": sorted(unanswered)}
                            continue
                        differing, _floor, _, _ = _compare(run, comparison=w.SAME_DEPLOYMENT, channel=channel)
                        outcomes[cell] = (
                            {"outcome": "distinguishable", "at": sorted(differing)}
                            if differing
                            else {"outcome": "indistinguishable"}
                        )
    finally:
        for name, level in levels.items():
            logging.getLogger(name).setLevel(level)
    assert not unconstructed, f"the counterexample was not constructed (the probe was not answered with nothing): {unconstructed}"
    expected = {f"{w.SAME_DEPLOYMENT}-{r}-{a}-{d}-{c}" for r, a, d, c in _p6_limitation_cells()}
    assert set(outcomes) == expected, f"a probe-limitation cell was not measured: {sorted(expected - set(outcomes))}"
    counts: dict[str, int] = {}
    for found in outcomes.values():
        counts[found["outcome"]] = counts.get(found["outcome"], 0) + 1
    record_testsuite_property("p6_probe_limitation", json.dumps(
        {"cells": len(outcomes), "counts": counts, "outcomes": outcomes}, sort_keys=True
    ))
    lines = [
        "",
        "=" * 30 + " SEC-020 P6 PROBE LIMITATION (reported, NOT in the gate) " + "=" * 30,
        f"a source that recognizes the probe identifier (exactly, or by its shape), {len(outcomes)} same-deployment"
        f" cells measured on this run: {json.dumps(counts, sort_keys=True)}",
        *(f"  {cell}: {found['outcome']}" + (f" at {found['at']}" if "at" in found else "")
          for cell, found in sorted(outcomes.items())),
        "=" * 117,
    ]
    with capsys.disabled():
        print("\n".join(lines))


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
    if channel == w.REFERENCE and not w.p6_refused(run):
        # Q11, as in the standing instrument: the reference channel is
        # instrumented by Q11's properties, never by a difference (under CT-A
        # extended to ruling P6 (a), by the twin's answer against the refusal,
        # below, as every channel of a refused shape is).
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


# =============================================================================
# E2 (ii): a class that affirms ``never`` whose projection withholds anyway
# =============================================================================
#
# Dave, 2026-10-08 12:29 MST (``D-IMPL-378``), verbatim: "E2 (ii) REJECTED as
# disclosure-only: The proposed hidden-subject exception versus
# nonexistent-subject 200 is a measured oracle. Validate withholding capability
# against the class declaration at construction; retain the runtime check as
# defense. Keep the violation probe visible until the treatment satisfies the
# closure criterion." The cells below are that probe, inside the closure gate:
# never retired, never marked, red for every configuration whose two sides a
# caller can still tell apart.


@pytest.fixture(scope="module")
def never_runs(tmp_path_factory: pytest.TempPathFactory) -> Iterator[w.NeverRunCache]:
    """One E2 (ii) run per (configuration, anchor, door) for this module."""
    levels = {name: logging.getLogger(name).level for name in _QUIETED_LOGGERS}
    for name in _QUIETED_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        yield w.NeverRunCache(lambda name: pathlib.Path(tmp_path_factory.mktemp(name)))
    finally:
        for name, level in levels.items():
            logging.getLogger(name).setLevel(level)


def _never_cells() -> list[Any]:
    cells = []
    for configuration, shape in w.NEVER_CONFIGURATIONS.items():
        for comparison in w.COMPARISONS:
            for anchor in w.ANCHORS:
                for door in w.DOORS:
                    for channel in w.channels_for(comparison=comparison, shape=shape, door=door):
                        cells.append(
                            pytest.param(
                                comparison, configuration, anchor, door, channel,
                                id=f"{comparison}-{configuration}-{anchor}-{door}-{channel}",
                            )
                        )
    return cells


def _both_raised(run: w.Run, *sides: str, either: bool = False, excused: tuple[str, ...] = ()) -> dict[str, dict[str, str]]:
    """Positions where the named sides RAISED instead of answering — :func:`_vacuous` with no shape's excuse.

    Nothing is excused here by the shape a configuration follows: a raise is
    "not evidence" unless the side is named in ``excused`` and what it raised
    is one of :data:`~tests.products.sec020_worlds.NEVER_CONSTRUCTION_REFUSALS`
    at its one question (the instrument's refused side, CT-A (a)).
    """
    raised = {side: run.raised(side) for side in sides}
    positions = set().union(*(set(r) for r in raised.values()))
    found: dict[str, dict[str, str]] = {}
    for position in sorted(positions):
        hit = {
            side: r[position]
            for side, r in raised.items()
            if position in r
            and not (
                side in excused
                and position == w.ONLY
                and any(r[position].startswith(f"{name}:") for name in w.NEVER_CONSTRUCTION_REFUSALS)
            )
        }
        if (either and hit) or (hit and all(position in r for r in raised.values())):
            found[position] = hit
    return found


@pytest.mark.parametrize(("comparison", "configuration", "anchor", "door", "channel"), _never_cells())
def test_a_withheld_subject_under_a_never_class_is_indistinguishable(
    never_runs: w.NeverRunCache, comparison: str, configuration: str, anchor: str, door: str, channel: str
) -> None:
    """E2 (ii): under a class affirming ``never``, a withheld subject is indistinguishable from a nonexistent one.

    The class affirms ``subject_withholding: never`` and its projection
    withholds the subject anyway, in each way the two can meet
    (``sec020_worlds.NEVER_CONFIGURATIONS``). Judged by this module's own rules:
    the same pairs, noise floor and kind rule as
    :func:`test_withheld_is_indistinguishable`, and two sides that both raised
    are "not evidence". The refusals this cell holds as the property are the
    composition's own, raised where its resolver is built
    (``sec020_worlds.NEVER_CONSTRUCTION_REFUSALS``: the declared capability,
    and since Dave's E2 (ii) (d) the missing positive declaration) — and only
    when the withheld, nonexistent and noise-floor sides ALL observe the SAME
    one, by name, and the same configuration without its withholding
    capability — the policy off, positively declaring that it never withholds —
    answers rather than raising (``sec020_worlds.NEVER_TWIN``): Dave's CT-A (a),
    "Construction refusal counts, paired with a declared twin that successfully
    answers." A refusal raised when the projection withholds — for the withheld
    subject only — is the oracle Dave ruled, and this cell fails on it.
    """
    run = never_runs.get(configuration=configuration, anchor=anchor, door=door)
    withheld_side, nonexistent_side, floor_side = w.PAIRS[comparison]
    if w.never_refused_at_construction(run, (withheld_side, nonexistent_side, floor_side)):
        # As P2 (c)'s twin is held (``test_an_undeclared_composite_is_refused_where_its_resolver_is_built``):
        # the twin ANSWERS — served, or refused as data — and does not raise.
        assert not run.raised(w.NEVER_TWIN), (
            f"E2 (ii) [{comparison}, {configuration}, {anchor}, {door}]: control: the configuration without its"
            f" withholding capability raised, so the refusal every side observed is not evidence that the"
            f" capability is what it refuses: {run.raised(w.NEVER_TWIN)}"
        )
        return
    vacuous = _both_raised(run, withheld_side, nonexistent_side)
    assert not vacuous, (
        f"E2 (ii) [{comparison}, {configuration}, {anchor}, {door}, {channel}]: not evidence — both sides"
        f" RAISED instead of answering, and two equal exceptions are equal on every channel: {vacuous}"
    )
    differing, floor, withheld, nonexistent = _compare(run, comparison=comparison, channel=channel)
    assert not differing, (
        f"E2 (ii) [{comparison}, {configuration}, {anchor}, {door}, {channel}]: under a class affirming never,"
        f" a withheld subject is distinguishable from a nonexistent one at {sorted(differing)}"
        f" (noise floor, not counted: {sorted(floor)})\n"
        f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
    )


def _never_instruments() -> list[Any]:
    params = []
    for configuration, shape in w.NEVER_CONFIGURATIONS.items():
        for anchor in w.ANCHORS:
            for door in w.DOORS:
                channels: set[str] = set()
                for comparison in w.COMPARISONS:
                    channels |= set(w.channels_for(comparison=comparison, shape=shape, door=door))
                for channel in sorted(channels):
                    params.append(pytest.param(configuration, anchor, door, channel,
                                               id=f"{configuration}-{anchor}-{door}-{channel}"))
    return params


@pytest.mark.parametrize(("configuration", "anchor", "door", "channel"), _never_instruments())
def test_the_never_instrument_sees_a_difference(
    never_runs: w.NeverRunCache, configuration: str, anchor: str, door: str, channel: str
) -> None:
    """The instrument of every E2 (ii) channel: a side that differs from the nonexistent one MUST be seen to differ.

    As :func:`test_the_instrument_sees_a_difference`: the subject SERVED (the
    configuration without its withholding capability,
    ``sec020_worlds.NEVER_TWIN``) against the nonexistent side; for refusal
    codes, the question its class refuses by contract; for references, Dave's
    Q11 properties. Where the nonexistent side observed a construction
    refusal by name (``sec020_worlds.NEVER_CONSTRUCTION_REFUSALS``), every
    channel is instrumented by the twin answering against it — the structural
    pair of :func:`test_an_undeclared_composite_is_refused_where_its_resolver_is_built`.
    """
    run = never_runs.get(configuration=configuration, anchor=anchor, door=door)
    refused = w.never_refused_at_construction(run, (w.CF_NONEXISTENT,))
    if channel == w.REFERENCE and not refused:
        problems = w.reference_properties(run)
        assert not problems, (
            f"E2 (ii) reference instrument [{configuration}, {anchor}, {door}]: Dave's Q11 properties do not"
            f" hold, so a PASS of the reference comparison would prove nothing: {problems}"
        )
        return
    left_side = w.REFUSED_QUESTION if channel == w.REFUSAL and not refused else w.NEVER_TWIN
    right_side = w.CF_NONEXISTENT
    vacuous = _both_raised(run, left_side, right_side, either=True, excused=(right_side,))
    assert not vacuous, (
        f"E2 (ii) instrument not evidence [{configuration}, {anchor}, {door}, {channel}]: a side RAISED instead"
        f" of answering, so a difference it shows is the exception's, not the channel's: {vacuous}"
    )
    left = run.channel(left_side, channel)
    right = run.channel(right_side, channel)
    floor = w.diff_paths(right, run.channel(w.CF_FLOOR, channel))
    seen = w.diff_paths(left, right) - floor
    assert seen, (
        f"E2 (ii) instrument broken [{configuration}, {anchor}, {door}, {channel}]: {left_side} and"
        f" {right_side} are indistinguishable on this channel, so a PASS of its comparison would prove"
        f" nothing\n  {left_side}: {w.render(left)}\n  {right_side}: {w.render(right)}"
    )


# =============================================================================
# E2 (ii) (d): the FALSE-declaration counterexample — measured, reported, never gated
# =============================================================================


def _false_declaration_cells() -> list[str]:
    """Every cell the residual configurations would have, by the gate's own channel rule (never generated as gate cells)."""
    return [
        f"{comparison}-{configuration}-{anchor}-{door}-{channel}"
        for configuration, shape in w.NEVER_FALSE_DECLARATION_CONFIGURATIONS.items()
        for comparison in w.COMPARISONS
        for anchor in w.ANCHORS
        for door in w.DOORS
        for channel in w.channels_for(comparison=comparison, shape=shape, door=door)
    ]


def test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated(
    never_runs: w.NeverRunCache, record_testsuite_property: Callable[[str, object], None], capsys: Any
) -> None:
    """Dave's E2 (ii) (d): the false-declaration counterexample, executed and reported every run, never gated.

    Dave, 2026-10-08 16:40 MST (``D-IMPL-378``), verbatim: *"Require a positive
    declaration, default silence to refusal, and explicitly limit the
    trusted-code assumption to deployment code callers cannot influence. Keep
    the false-declaration counterexample visible."* A plan factory that
    positively declares it never withholds while its projection withholds
    (``sec020_worlds.NEVER_FALSE_DECLARATION_CONFIGURATIONS``) is built — the
    declaration is trusted deployment code — and its withheld subject's
    question meets the serve-time defense alone. Every cell those
    configurations would have is run here through exactly what a gate cell
    runs — :func:`never_refused_at_construction`'s CT-A (a) test, then
    :func:`_both_raised`, then :func:`_compare` — and classified:
    ``distinguishable``, ``indistinguishable``, ``not evidence`` (both sides
    raised) or ``refused at construction`` (the configuration was not the
    residual at all).

    **What this asserts, and what it does not.** That every cell was MEASURED,
    and nothing about the outcome: the cells are the reported residual of a
    trusted-code assumption, not evidence for SEC-020, so how many are
    distinguishable never moves the gate. The measurement is printed past the
    output capture in its own block, headed
    ``SEC-020 E2 (ii) FALSE-DECLARATION LIMITATION``, and recorded in the JUnit
    record as ``e2ii_false_declaration_limitation`` — the same treatment as
    :func:`test_d1a_limitation_the_retired_two_deployment_cells_are_measured_not_gated`.
    No skip and no expected-failure mark hides it. The counterexample's own
    test, which asserts it still holds, is
    ``tests/products/test_sec020_e2ii_trusted_declaration.py::test_e2ii_d_counterexample_a_false_positive_declaration_still_tells_the_withheld_subject_apart``.

    **A floor copy that did not answer** (Dave, 2026-10-09, ``D-IMPL-378``: *"A failed spare answer cannot excuse
    differences. Apply the check to the gate and limitation measurements"*). A cell whose noise floor's copy raised
    (:func:`_floor_copy_did_not_answer`) is classified :data:`FLOOR_COPY_OUTCOME`, by name, with what the copy
    raised, and is never judged off that floor: it was not measured, so it is reported as neither distinguishable
    nor indistinguishable, in the same block and the same JUnit record.
    """
    outcomes: dict[str, dict[str, Any]] = {}
    for cell in _false_declaration_cells():
        comparison, configuration, anchor, door, channel = cell.split("-")
        run = never_runs.get(configuration=configuration, anchor=anchor, door=door)
        withheld_side, nonexistent_side, floor_side = w.PAIRS[comparison]
        if w.never_refused_at_construction(run, (withheld_side, nonexistent_side, floor_side)):
            outcomes[cell] = {"outcome": "refused at construction", "raised": run.raised(withheld_side).get(w.ONLY, "")}
            continue
        vacuous = _both_raised(run, withheld_side, nonexistent_side)
        if vacuous:
            outcomes[cell] = {"outcome": "not evidence", "raised": sorted(vacuous)}
            continue
        unanswered = _floor_copy_did_not_answer(run, comparison)
        if unanswered:
            outcomes[cell] = {"outcome": FLOOR_COPY_OUTCOME, "raised": sorted(unanswered)}
            continue
        differing, _floor, _, _ = _compare(run, comparison=comparison, channel=channel)
        found: dict[str, Any] = (
            {"outcome": "distinguishable", "at": sorted(differing)} if differing else {"outcome": "indistinguishable"}
        )
        withheld_raised = run.raised(withheld_side).get(w.ONLY, "")
        if withheld_raised:
            found["withheld_raised"] = withheld_raised.split(":", 1)[0]
        outcomes[cell] = found
    assert sorted(outcomes) == sorted(_false_declaration_cells()), "a false-declaration cell was not measured"
    counts: dict[str, int] = {}
    for found in outcomes.values():
        counts[found["outcome"]] = counts.get(found["outcome"], 0) + 1
    record_testsuite_property("e2ii_false_declaration_limitation", json.dumps(
        {"cells": len(outcomes), "counts": counts, "outcomes": outcomes}, sort_keys=True
    ))
    lines = [
        "",
        "=" * 25 + " SEC-020 E2 (ii) FALSE-DECLARATION LIMITATION (reported, NOT in the gate) " + "=" * 25,
        f"the {len(outcomes)} cells of a never class over a plan factory that falsely declares it never"
        f" withholds, measured on this run: {json.dumps(counts, sort_keys=True)}",
        *(f"  {cell}: {found['outcome']}" + (f" at {found['at']}" if "at" in found else "")
          + (f" (withheld side raised {found['withheld_raised']})" if "withheld_raised" in found else "")
          for cell, found in sorted(outcomes.items())),
        "=" * 124,
    ]
    with capsys.disabled():
        print("\n".join(lines))


# =============================================================================
# The noise floor's own copy must have ANSWERED (Dave, 2026-10-09; the final panel's BLD-1, G-FLOOR-COPY)
# =============================================================================
#
# Dave, 2026-10-09 06:06 MST (``D-IMPL-378``), verbatim (kept as a comment, CINV-01a): "Also strengthen the closure
# test's noise-floor control: prove that the control successfully answered before using it to excuse differences.
# Obtain explicit approval for that test amendment." 06:21 MST: "Floor change approved. A failed spare answer cannot
# excuse differences. Apply the check to the gate and limitation measurements; rerun and report any changed counts."
#
# The gap (the final panel's BLD-1): every comparison reads its noise floor off a second copy of the nonexistent
# side, but only the two COMPARED sides were checked for having raised. A floor copy that raised while the compared
# sides answered differs from the nonexistent answer at every path, so its floor excused every value and missing-key
# difference between the withheld side and the nonexistent one. The tests below hold the closing test's own judging
# code to the amendment on SYNTHETIC runs (no deployment is built): the compared sides answer with two different
# refusal codes and the floor's copy RAISED, as ``sec020_worlds.observe_mcp`` records an unreachable door. Every site
# that reads a noise floor is held: the gate cell, the never-class cell, and the three reported limitation
# measurements (D1 (a), ruling P6 (a)'s probe, E2 (ii) (d)'s false declaration).

#: The named reason a cell fails by when its floor's copy did not answer: an ``AssertionError`` of this type name.
FLOOR_COPY_REFUSAL = "FloorCopyDidNotAnswer"
#: The outcome a limitation measurement reports such a cell under, by name: neither distinguishable nor
#: indistinguishable, because no noise floor was measured.
FLOOR_COPY_OUTCOME = "floor copy raised"

_FLOOR_WITHHELD = {"outcome": "refused", "code": "subject-withheld", "detail": "refused"}
_FLOOR_NONEXISTENT = {"outcome": "refused", "code": "subject-not-found", "detail": "refused"}
_FLOOR_UNREACHABLE = {"outcome": "unreachable", "detail": "MCP unreachable: session crashed"}
_FLOOR_RAISED = "MCP unreachable: session crashed"


def _floor_observation(value: Any, *, raised: dict[str, str] | None = None) -> w.Observation:
    """One synthetic side: ``value`` on every channel; ``raised``, what its question ended in instead of answering."""
    return w.Observation(channels={channel: value for channel in w.CHANNELS}, raw=value, raised=dict(raised or {}))


def _floor_world(*, shape: str = w.SUBJECT_KEYED, withheld: Any = None, floor_raised: bool = True) -> w.Run:
    """A synthetic run: the compared sides answer; both comparisons' floor copies RAISED, or answered like the nonexistent side."""
    floor = (
        _floor_observation(_FLOOR_UNREACHABLE, raised={w.ONLY: _FLOOR_RAISED})
        if floor_raised
        else _floor_observation(_FLOOR_NONEXISTENT)
    )
    return w.Run(
        shape=shape,
        anchor=w.FROM_DECISION,
        door=w.MCP,
        sides={
            w.CF_WITHHELD: _floor_observation(_FLOOR_WITHHELD if withheld is None else withheld),
            w.CF_NONEXISTENT: _floor_observation(_FLOOR_NONEXISTENT),
            w.SAME_NONEXISTENT: _floor_observation(_FLOOR_NONEXISTENT),
            w.CF_FLOOR: floor,
            w.SAME_FLOOR: floor,
        },
    )


class _OneRun:
    """A run cache that answers every ``get`` with one synthetic run."""

    def __init__(self, run: w.Run) -> None:
        self._run = run

    def get(self, **_: str) -> w.Run:
        return self._run


class _Recorded:
    """``record_testsuite_property``, kept so the test can read the measurement back."""

    def __init__(self) -> None:
        self.properties: dict[str, Any] = {}

    def __call__(self, name: str, value: object) -> None:
        self.properties[name] = json.loads(str(value))


class _NoCapture:
    """``capsys`` for a limitation measurement driven directly: its block prints, uncaptured."""

    def disabled(self) -> Any:
        import contextlib  # noqa: PLC0415

        return contextlib.nullcontext()


def _floor_fails_by_name(cell: Callable[[], None]) -> AssertionError:
    """Run one cell; it must FAIL, by the named floor-copy reason."""
    with pytest.raises(AssertionError) as failed:
        cell()
    assert type(failed.value).__name__ == FLOOR_COPY_REFUSAL, (
        f"the cell failed, but not because its floor's copy did not answer: {type(failed.value).__name__}: {failed.value}"
    )
    return failed.value


def _floor_outcomes_by_name(outcomes: dict[str, dict[str, Any]], expected: list[str]) -> None:
    """Every expected cell was measured, and every one is reported under the floor-copy outcome, by name."""
    assert sorted(outcomes) == sorted(expected), "a cell of the limitation was not measured"
    wrong = {cell: found for cell, found in outcomes.items() if found.get("outcome") != FLOOR_COPY_OUTCOME}
    assert not wrong, (
        f"{len(wrong)} of {len(outcomes)} cells whose floor copy RAISED were judged off that floor anyway:"
        f" {dict(list(wrong.items())[:3])}"
    )


def test_a_floor_copy_that_raised_cannot_excuse_a_gate_cell() -> None:
    """The gap as the panel executed it (BLD-1): ``subject-withheld`` against ``subject-not-found``, the floor's copy raised.

    Before the amendment the floor read off the raised copy differed from the nonexistent side at every path and
    excused the code difference, so the cell PASSED. After it, the cell fails by name (:data:`FLOOR_COPY_REFUSAL`).
    """
    run = _floor_world()
    _floor_fails_by_name(
        lambda: test_withheld_is_indistinguishable(
            _OneRun(run), w.COUNTERFACTUAL, w.SUBJECT_KEYED, w.FROM_DECISION, w.MCP, w.RESPONSE
        )
    )


def test_a_floor_copy_raising_the_held_refusal_where_the_copied_side_answered_cannot_excuse() -> None:
    """A raise that is a held refusal elsewhere is no floor where the side it copies ANSWERED.

    The reused fabric's second question: both compared sides answered it (with different codes) and only the floor's
    copy raised ``AcquiredFabricReused`` there, the refusal Q9's cells hold as the property when every side raises
    it. The floor then compares a refusal with an answer, so it cannot excuse anything.
    """
    raised = {"second": "AcquiredFabricReused: synthetic"}
    run = _floor_world(shape=w.REUSED_FABRIC)
    for side, value in ((w.CF_WITHHELD, _FLOOR_WITHHELD), (w.CF_NONEXISTENT, _FLOOR_NONEXISTENT)):
        run.sides[side] = _floor_observation({"first": _FLOOR_NONEXISTENT, "second": value})
    run.sides[w.CF_FLOOR] = _floor_observation({"first": _FLOOR_NONEXISTENT, "second": _FLOOR_UNREACHABLE}, raised=raised)
    _floor_fails_by_name(
        lambda: test_withheld_is_indistinguishable(
            _OneRun(run), w.COUNTERFACTUAL, w.REUSED_FABRIC, w.FROM_DECISION, w.IN_PROCESS, w.RESPONSE
        )
    )


def test_a_floor_copy_that_raised_cannot_excuse_a_never_class_cell() -> None:
    """E2 (ii)'s gate cells judge by the same floor: the same synthetic run fails there by name too."""
    run = _floor_world()
    _floor_fails_by_name(
        lambda: test_a_withheld_subject_under_a_never_class_is_indistinguishable(
            _OneRun(run), w.COUNTERFACTUAL, w.NEVER_LATE, w.FROM_DECISION, w.MCP, w.RESPONSE
        )
    )


def test_a_floor_copy_that_raised_is_reported_by_name_in_the_d1a_limitation() -> None:
    """D1 (a)'s reported limitation: a retired cell whose floor copy raised is reported under its own outcome, by name."""
    recorded = _Recorded()
    test_d1a_limitation_the_retired_two_deployment_cells_are_measured_not_gated(
        _OneRun(_floor_world()), recorded, _NoCapture()
    )
    _floor_outcomes_by_name(recorded.properties["d1a_limitation"]["outcomes"], list(RETIRED_D1A))


def test_a_floor_copy_that_raised_is_reported_by_name_in_the_p6_limitation(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ruling P6 (a)'s reported counterexample: a cell whose floor copy raised is reported under its own outcome, by name.

    The counterexample's world is replaced by the synthetic run, its notes saying the probe was asked first and
    answered nothing each time, so the measurement reaches its comparison.
    """
    probe = w.probe_identifier()
    run = _floor_world(shape=w.PROBE_RECOGNIZING)
    run.notes = {"asked": [probe, w.SUBJECT, probe, w.NEVER, probe, w.NEVER_2], "answered_nothing_for": [probe] * 3}
    monkeypatch.setattr(w, "probe_recognizing_run", lambda base, **_: run)
    recorded = _Recorded()
    test_p6_limitation_a_source_that_recognizes_the_probe_is_measured_not_gated(
        tmp_path_factory, recorded, _NoCapture()
    )
    expected = [f"{w.SAME_DEPLOYMENT}-{r}-{a}-{d}-{c}" for r, a, d, c in _p6_limitation_cells()]
    _floor_outcomes_by_name(recorded.properties["p6_probe_limitation"]["outcomes"], expected)


def test_a_floor_copy_that_raised_is_reported_by_name_in_the_e2ii_limitation() -> None:
    """E2 (ii) (d)'s reported false-declaration cells: a cell whose floor copy raised is reported under its own outcome."""
    recorded = _Recorded()
    test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated(
        _OneRun(_floor_world()), recorded, _NoCapture()
    )
    _floor_outcomes_by_name(
        recorded.properties["e2ii_false_declaration_limitation"]["outcomes"], _false_declaration_cells()
    )


def test_control_an_answering_floor_copy_still_counts_the_difference() -> None:
    """Control: the floor's copy ANSWERED like the nonexistent side — the cell fails as before, at the code, as distinguishable."""
    run = _floor_world(floor_raised=False)
    with pytest.raises(AssertionError) as failed:
        test_withheld_is_indistinguishable(
            _OneRun(run), w.COUNTERFACTUAL, w.SUBJECT_KEYED, w.FROM_DECISION, w.MCP, w.RESPONSE
        )
    assert type(failed.value) is AssertionError, f"{type(failed.value).__name__}: {failed.value}"
    assert "is distinguishable from a nonexistent one at ['code']" in str(failed.value), failed.value


def test_control_equal_answers_over_an_answering_floor_copy_pass() -> None:
    """Control: the compared sides answer alike and the floor's copy answered — the cell passes."""
    run = _floor_world(withheld=_FLOOR_NONEXISTENT, floor_raised=False)
    test_withheld_is_indistinguishable(
        _OneRun(run), w.COUNTERFACTUAL, w.SUBJECT_KEYED, w.FROM_DECISION, w.MCP, w.RESPONSE
    )


def test_control_a_floor_copy_raising_the_held_refusal_with_the_copied_side_still_floors() -> None:
    """Control: Q9's reused store — every side raised the held refusal at both positions; the cell passes as before.

    The floor's copy raised exactly what the side it copies raised, the refusal the cell holds as its property, so
    the floor compares a refusal with a refusal and stays a floor: the amendment does not turn the property's cells red.
    """
    refusal = "AcquisitionNeedsAQuestionFabric: synthetic"
    shape_of = {"outcome": "raised", "type": "AcquisitionNeedsAQuestionFabric", "message": "synthetic"}
    both = {"first": shape_of, "second": shape_of}
    raised = {"first": refusal, "second": refusal}
    run = w.Run(
        shape=w.REUSED_STORE,
        anchor=w.FROM_DECISION,
        door=w.IN_PROCESS,
        sides={side: _floor_observation(both, raised=raised) for side in (w.CF_WITHHELD, w.CF_NONEXISTENT, w.CF_FLOOR)},
    )
    test_withheld_is_indistinguishable(
        _OneRun(run), w.COUNTERFACTUAL, w.REUSED_STORE, w.FROM_DECISION, w.IN_PROCESS, w.RESPONSE
    )


# --- the amendment itself (Dave, 2026-10-09 06:06 MST, approved 06:21 MST, D-IMPL-378) ---------------------------


class FloorCopyDidNotAnswer(AssertionError):
    """A cell's noise floor was read off a copy that RAISED: not evidence, by name, and the floor excuses nothing.

    Dave, 2026-10-09 (``D-IMPL-378``), approved at 06:21 MST: *"A failed spare answer cannot excuse differences."*
    An ``AssertionError``, so a gate or never-class cell that meets it FAILS. A limitation measurement asks
    :func:`_floor_copy_did_not_answer` before it compares and reports the cell by :data:`FLOOR_COPY_OUTCOME`.
    """


def _floor_copy_did_not_answer(run: w.Run, comparison: str) -> dict[str, str]:
    """Where the noise floor's copy RAISED in a way that leaves it nothing to measure: position, and what it raised.

    The floor is read off a second copy of the nonexistent side (``sec020_worlds.PAIRS``), and measures that side's
    own variation only where the copy did what the side does. Where the copy raised, that holds only if the
    nonexistent side raised at the same position too, and both raised the refusal this proof holds as the property
    there: Q9's reuse refusals and P2 (c)'s construction refusal (``sec020_worlds.raising_is_the_property``), ruling
    P6 (a)'s refusal (``sec020_worlds.p6_refusal_is_the_property``). The floor then compares a refusal with a refusal.
    Every other raise of the copy, at its question or inside one of its record reads (``<position>/record:<read>``,
    never the property), leaves the floor comparing an exception with an answer, which differs at every path and
    would excuse every difference. Those are returned, and while any is, the floor may excuse nothing.
    """
    _withheld_side, nonexistent_side, floor_side = w.PAIRS[comparison]
    copied = run.raised(nonexistent_side)

    def held(position: str, raised: str) -> bool:
        return (
            w.raising_is_the_property(run.shape, position, raised)
            or w.p6_refusal_is_the_property(run, position, raised)
            or w.held_refusal_is_the_property(run, position, raised)
        )

    unanswered: dict[str, str] = {}
    for position, raised in sorted(run.raised(floor_side).items()):
        if not (position in copied and held(position, raised) and held(position, copied[position])):
            unanswered[position] = raised
    return unanswered


def _require_the_floor_copy_answered(run: w.Run, comparison: str) -> None:
    """The amendment where every noise floor of this module is read (:func:`_compare`): fail by name, before any excuse."""
    unanswered = _floor_copy_did_not_answer(run, comparison)
    if unanswered:
        _withheld_side, _nonexistent_side, floor_side = w.PAIRS[comparison]
        raise FloorCopyDidNotAnswer(
            f"SEC-020 [{comparison}, {run.shape}, {run.anchor}, {run.door}]: not evidence, the noise floor's copy"
            f" ({floor_side}) RAISED instead of answering, and a failed spare answer cannot excuse a difference:"
            f" {unanswered}"
        )


# =============================================================================
# X17 (a): the pin channel (Dave, 2026-10-09 06:06 MST, confirmed 06:21 MST, D-IMPL-378)
# =============================================================================


@pytest.fixture(scope="module")
def pin_runs(tmp_path_factory: pytest.TempPathFactory) -> Iterator[w.PinRunCache]:
    """One pin-channel run per (shape, anchor) for this module."""
    levels = {name: logging.getLogger(name).level for name in _QUIETED_LOGGERS}
    for name in _QUIETED_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        yield w.PinRunCache(lambda name: pathlib.Path(tmp_path_factory.mktemp(name)))
    finally:
        for name, level in levels.items():
            logging.getLogger(name).setLevel(level)


@pytest.fixture(scope="module")
def pin_instrument(tmp_path_factory: pytest.TempPathFactory) -> Iterator[w.PinInstrument]:
    """The pin channel's instrument readings, read once for this module."""
    levels = {name: logging.getLogger(name).level for name in _QUIETED_LOGGERS}
    for name in _QUIETED_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        yield w.pin_instrument(pathlib.Path(tmp_path_factory.mktemp("pin-instrument")))
    finally:
        for name, level in levels.items():
            logging.getLogger(name).setLevel(level)


def _pin_cells() -> list[Any]:
    """One cell per shape, anchor and pin surface; each holds every one-sided pin of its run, in both directions."""
    return [
        pytest.param(shape, anchor, surface, id=f"{shape}-{anchor}-{surface}")
        for shape in ALL_SHAPES
        for anchor in w.ANCHORS
        for surface in w.PIN_SURFACES
    ]


def _pin_questions(runs: w.RunCache, pin_run: w.PinRun) -> w.Run:
    """The pin channel's questions, as the gate judges the same shape's questions.

    The gate's own in-process run of the same shape and anchor, its three counterfactual sides replaced by the pin
    channel's deployments. A refusal the gate holds as the property is held here exactly when it is held there and
    these deployments observed it too, word for word: ruling P6 (a)'s refusal is held only together with that run's
    declared-population twin answering and its other probed sides refused alike (``sec020_worlds.p6_refused``).
    """
    gate = runs.get(shape=pin_run.shape, anchor=pin_run.anchor, door=w.IN_PROCESS)
    return w.Run(
        shape=pin_run.shape, anchor=pin_run.anchor, door=w.IN_PROCESS, sides={**gate.sides, **pin_run.questions}
    )


@pytest.mark.parametrize(("shape", "anchor", "surface"), _pin_cells())
def test_a_pin_filed_in_one_deployment_reads_alike_in_both(
    runs: w.RunCache, pin_runs: w.PinRunCache, shape: str, anchor: str, surface: str
) -> None:
    """X17 (a): a pin filed in only ONE of the two deployments reads ALIKE in both, at every surface the asker reads it.

    Dave, 2026-10-09 06:06 MST (``D-IMPL-378``), item 1, confirmed at 06:21 MST ("X17(a)"), verbatim: *"Cover
    versioned resolution and write-then-read in the closure gate. Keep attacker address derivation labeled unproven
    until demonstrated; it does not excuse the inconsistent authorization."* Option (a), lane ``378h-names``'s P-2:
    *"Add the channel with every read. The gate goes red on the resolution resource until that is addressed."*

    **The channel** (``sec020_worlds.pin_run``). The counterfactual's two deployments (the withholding one, and the
    one whose source does not hold the subject) and the noise floor's copy are each asked the same question in
    process. Every executed-query pin their records name that is filed in exactly ONE of the two (filing read off
    each store before anything is written) is read as the asker in all three: the MCP artifact server's names,
    blob, presence and versioned-URI resolution (``ccf-artifact://{tenant}/{class}/{name}@{version}``, under every
    name the filing deployment filed it), and the HTTP door's ``/artifact/{content_address}``, ``/replay/decisions``
    and ``/replay/resolutions``, through the record channel's own reads (the asker, and another principal of the
    tenant). Then WRITE-THEN-READ: the asker files the pin's canonical bytes on its own client lane
    (``put_artifact``) and reads them back through blob, presence and names. One cell per shape, anchor and surface;
    each cell holds every one-sided pin of its run, in both directions.

    **Judged by the gate's own rules.** The questions first: two compared sides that raised, other than as the
    refusal the gate holds as the property for this shape, are not evidence (:func:`_vacuous`, over
    :func:`_pin_questions`), and the noise floor's copy must have answered (:func:`_require_the_floor_copy_answered`).
    The floor's copy must also have filed every one-sided pin exactly where the not-holding deployment did, or its
    readings are not a floor. Then each reading: :func:`_vacuous`, then :func:`_compare` (the noise floor, the kind
    rule, the reference form, and the floor-copy rule).

    **Unproven, and no excuse.** The canonical bytes the asker writes are read here from the deployment that filed
    the pin, and each pin's address from the deployment's own record, as an auditor reads them. An outsider
    recomputing a pin's address WITHOUT the record, from what it asked and from public documents, is UNREPRODUCED:
    unproven until demonstrated. That does not excuse the channel. These cells count regardless, and a cell that is
    red here is red in the gate.

    **Expected on this tree.** The versioned-URI resolution and the three write-then-read reads tell the two
    deployments apart wherever a pin is one-sided (``D-IMPL-378`` F1-1b and F1-1c: open, design-first), so those
    cells are RED, and none is marked, skipped or excluded. At two population-reading shapes a pin is one-sided under
    ``from_entity_freshness`` too, because there the deployment whose source holds the subject serves where the other
    refuses: D1 (a)'s confound, which this module's D1 (a) block reports, at the outcome, for those shapes'
    two-deployment cells. D1 (a) retires the other channels' two-deployment cells of those shapes; no ruling retires
    these, so they are in the gate.

    **Not reached.** A composite's children answer through records that the parent's record does not name in these
    worlds (its ``child_replay_ref`` is empty), so the pins those children file are outside this channel.
    """
    _require(shape)
    pin_run = pin_runs.get(shape=shape, anchor=anchor)
    questions = _pin_questions(runs, pin_run)
    vacuous = _vacuous(questions, w.CF_WITHHELD, w.CF_NONEXISTENT)
    assert not vacuous, (
        f"SEC-020 pin channel [{shape}, {anchor}, {surface}]: not evidence, both deployments' questions RAISED"
        f" instead of answering, so neither filed anything to compare: {vacuous}"
    )
    _require_the_floor_copy_answered(questions, w.COUNTERFACTUAL)
    unfaithful = {
        pin: {side: pin_run.filed[side][pin] for side in (w.CF_NONEXISTENT, w.CF_FLOOR)}
        for pin in pin_run.one_sided
        if pin_run.filed[w.CF_FLOOR][pin] != pin_run.filed[w.CF_NONEXISTENT][pin]
    }
    assert not unfaithful, (
        f"SEC-020 pin channel [{shape}, {anchor}, {surface}]: not evidence, the noise floor's copy did not file"
        f" these pins where the not-holding deployment did, so its readings are no floor: {unfaithful}"
    )
    found: dict[str, Any] = {}
    for pin in pin_run.one_sided:
        where = "filed where the subject is held" if pin_run.filed[w.CF_WITHHELD][pin] else "filed where it is not"
        run = pin_run.surface_run(pin, surface)
        vacuous = _vacuous(run, w.CF_WITHHELD, w.CF_NONEXISTENT)
        if vacuous:
            found[f"{pin} ({where})"] = f"not evidence, both readings failed: {vacuous}"
            continue
        differing, floor, withheld, nonexistent = _compare(run, comparison=w.COUNTERFACTUAL, channel=w.PIN)
        if differing:
            found[f"{pin} ({where})"] = {
                "at": sorted(differing),
                "noise floor, not counted": sorted(floor),
                "withholding deployment": w.render(withheld, limit=400),
                "not-holding deployment": w.render(nonexistent, limit=400),
            }
    assert not found, (
        f"SEC-020 pin channel [{shape}, {anchor}, {surface}]: a pin filed in only one of the two deployments tells"
        f" them apart, {len(found)} of {len(pin_run.one_sided)} one-sided pins: {json.dumps(found, sort_keys=True)}"
    )


@pytest.mark.parametrize("surface", w.PIN_SURFACES)
def test_the_pin_instrument_sees_a_difference(pin_instrument: w.PinInstrument, surface: str) -> None:
    """The pin channel's instrument: every surface, read where it MUST answer differently, is seen to differ.

    In one deployment (``sec020_worlds.pin_instrument``), as the asker: the asker's own read-refusal record (read
    back to the principal it names) by its versioned URI, against an address nobody filed in that record's class,
    floored by a second such address; for write-then-read, the asker's own client-lane filing read after its put,
    against the same reads at those two addresses; for the put, a put of other bytes (and that put again, its floor).
    Compared as the gate's instruments compare: a side that raised is not evidence, and paths in the floor are not
    counted. The reads do not depend on the shape, so one instrument per surface holds every cell of that surface.
    """
    run = pin_instrument.surface_run(surface)
    vacuous = _vacuous(run, w.SERVED, w.CF_NONEXISTENT, either=True)
    assert not vacuous, (
        f"pin instrument not evidence [{surface}]: a side RAISED instead of answering, so a difference it shows is"
        f" the exception's, not the surface's: {vacuous}"
    )
    present = run.channel(w.SERVED, w.PIN)
    absent = run.channel(w.CF_NONEXISTENT, w.PIN)
    floor = w.diff_paths(absent, run.channel(w.CF_FLOOR, w.PIN))
    seen = w.diff_paths(present, absent) - floor
    assert seen, (
        f"pin instrument broken [{surface}]: the asker's own artifact and an address nobody filed read alike here,"
        f" so a PASS of the pin cells at this surface would prove nothing\n  present: {w.render(present)}\n"
        f"  absent:  {w.render(absent)}"
    )


def test_the_pin_channel_census_is_measured_and_reported(
    pin_runs: w.PinRunCache, record_testsuite_property: Callable[[str, object], None], capsys: Any
) -> None:
    """The pin channel's population, reported every run: which pins each run's records name and which are one-sided.

    Asserts only that every run of the channel was MEASURED (built, asked, read): which pins are one-sided is
    reported, never asserted, because a run whose two deployments file the same pins carries nothing on this
    channel, and that is a measurement too. Printed past the output capture, in its own block headed
    ``SEC-020 PIN CHANNEL CENSUS``, and recorded in the JUnit record as ``pin_channel_census``.
    """
    census: dict[str, dict[str, Any]] = {}
    for shape in ALL_SHAPES:
        if shape in w.PENDING_SHAPES and not w.PENDING_SHAPES[shape][1]():
            continue
        for anchor in w.ANCHORS:
            run = pin_runs.get(shape=shape, anchor=anchor)
            recorded = set(run.pins[w.CF_WITHHELD]) | set(run.pins[w.CF_NONEXISTENT])
            census[f"{shape}-{anchor}"] = {
                "pins named": {side: len(pins) for side, pins in sorted(run.pins.items())},
                "one-sided, filed where the subject is held": [p for p in run.one_sided if run.filed[w.CF_WITHHELD][p]],
                "one-sided, filed where it is not": [p for p in run.one_sided if run.filed[w.CF_NONEXISTENT][p]],
                "named, filed in neither": sum(
                    1 for p in recorded if not run.filed[w.CF_WITHHELD][p] and not run.filed[w.CF_NONEXISTENT][p]
                ),
                "questions raised": {side: sorted(o.raised) for side, o in sorted(run.questions.items()) if o.raised},
            }
    expected = [
        f"{shape}-{anchor}"
        for shape in ALL_SHAPES
        if not (shape in w.PENDING_SHAPES and not w.PENDING_SHAPES[shape][1]())
        for anchor in w.ANCHORS
    ]
    assert sorted(census) == sorted(expected), "a run of the pin channel was not measured"
    one_sided = sum(len(c["one-sided, filed where the subject is held"]) + len(c["one-sided, filed where it is not"])
                    for c in census.values())
    record_testsuite_property("pin_channel_census", json.dumps({"runs": len(census), "census": census}, sort_keys=True))
    lines = [
        "",
        "=" * 30 + " SEC-020 PIN CHANNEL CENSUS (reported; the cells are in the gate) " + "=" * 30,
        f"{len(census)} runs; {one_sided} one-sided pins read at {len(w.PIN_SURFACES)} surfaces each:",
        *(f"  {key}: {json.dumps(found, sort_keys=True)}" for key, found in sorted(census.items())),
        "=" * 126,
    ]
    with capsys.disabled():
        print("\n".join(lines))


# =============================================================================
# OWED-RULINGS-3 item 4 (b): a held refusal at the P6 probe — the refusal counts, paired with a working twin
# =============================================================================
#
# Dave, 2026-10-09 06:21 MST (``D-IMPL-378``), verbatim: "4(b), plus the
# closing-test case and a supported working twin". The option ruled
# (OWED-RULINGS-3, dl-378-record @ 3533cc89), verbatim: "Refuse when the probe
# call itself returns a held refusal (refuses every question to a source that
# refuses unknown identifiers)." CT-A (a), Dave, 2026-10-08 12:29 MST, verbatim:
# "Construction refusal counts, paired with a declared twin that successfully
# answers."
#
# A judging change, appended: the cells below sit beside the matrix and change
# nothing it judges. The deployment is the ``subject_keyed`` world with its
# source answering an identifier it does not hold with a HELD refusal
# (``sec020_worlds.HeldRefusalSource``) — before item 4 (b), the withheld
# subject was answered while an identifier nothing holds was refused as data,
# at every door. Every question of it is now refused,
# ``UnheldSubjectProbeRefused``, decided by the probe and never by the subject.
# That refusal counts as the property a cell holds only when every side of the
# run observed it, by name, with ONE message, AND the supported working twin —
# the same deployment with its source answering an unheld identifier with
# nothing, the gate's own ``subject_keyed`` world (``HELD_REFUSAL_TWIN``) —
# answered every one of the same questions, and the twin's own cell for the
# same comparison and channel is indistinguishable by the gate's rules.
# Anything less is judged exactly as a gate cell is: ``_vacuous``, then
# ``_compare``. SEC-020 stays OPEN.


@pytest.fixture(scope="module")
def held_refusal_runs(tmp_path_factory: pytest.TempPathFactory) -> Iterator[w.HeldRefusalRunCache]:
    """One held-refusal run per (anchor, door) for this module."""
    levels = {name: logging.getLogger(name).level for name in _QUIETED_LOGGERS}
    for name in _QUIETED_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        yield w.HeldRefusalRunCache(lambda name: pathlib.Path(tmp_path_factory.mktemp(name)))
    finally:
        for name, level in levels.items():
            logging.getLogger(name).setLevel(level)


def _held_refusal_refused(run: w.Run, twin: w.Run) -> bool:
    """CT-A (a) for item 4 (b): whether the held-refusal run's refusal is the property its cells hold.

    True only when every side of the run (``sec020_worlds.HELD_REFUSAL_SIDES``)
    ended its one question in ``UnheldSubjectProbeRefused``, by type name, with
    ONE message among them all, and the twin raised nothing for any of the same
    sides' questions.
    """
    refusals = {run.raised(side).get(w.ONLY, "") for side in w.HELD_REFUSAL_SIDES}
    if len(refusals) != 1 or not next(iter(refusals)).startswith(f"{w.HELD_REFUSAL_REFUSAL}:"):
        return False
    return not any(twin.raised(side).get(w.ONLY) for side in w.HELD_REFUSAL_SIDES)


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_a_held_refusal_at_the_probe_is_refused_for_every_question(
    held_refusal_runs: w.HeldRefusalRunCache, runs: w.RunCache, anchor: str, door: str
) -> None:
    """Item 4 (b), the refusal: every question of the held-refusal deployment refused alike, the twin answering.

    Every side — the withheld subject, two identifiers nothing holds, the
    counterfactual pair and an ordinarily served subject — observes
    ``UnheldSubjectProbeRefused``, by name, with one message, at every door
    (read by type behind HTTP and MCP off the resolver each door was handed);
    every source was handed the probe identifier and never an asked subject;
    and the supported working twin answered every one of the same questions,
    its served subject SERVED.
    """
    run = held_refusal_runs.get(anchor=anchor, door=door)
    twin = runs.get(shape=w.HELD_REFUSAL_TWIN, anchor=anchor, door=door)
    refusals = {side: run.raised(side).get(w.ONLY, "") for side in w.HELD_REFUSAL_SIDES}
    wrong = {
        side: refusal or w.render(run.channel(side, w.RESPONSE))
        for side, refusal in refusals.items()
        if not refusal.startswith(f"{w.HELD_REFUSAL_REFUSAL}:")
    }
    assert not wrong, f"[{anchor}, {door}] not refused by {w.HELD_REFUSAL_REFUSAL}: {wrong}"
    assert len(set(refusals.values())) == 1, (
        f"[{anchor}, {door}] the refusal must be worded once, whatever was asked: {sorted(set(refusals.values()))}"
    )
    probe = w.probe_identifier()
    handed = {name: asked for name, asked in run.notes["asked"].items() if set(asked) != {probe}}
    assert not handed, f"[{anchor}, {door}] a source was handed more than the probe identifier: {handed}"
    twin_raised = {side: twin.raised(side).get(w.ONLY) for side in w.HELD_REFUSAL_SIDES if twin.raised(side).get(w.ONLY)}
    assert not twin_raised, (
        f"[{anchor}, {door}] control: the supported working twin raised, so the refusal above is not"
        f" evidence that the held refusal is what it refuses: {twin_raised}"
    )
    served = twin.channel(w.SERVED, w.RESPONSE)
    if door == w.IN_PROCESS:
        answered = served.get("outcome") == "served"
    elif door == w.HTTP:
        answered = served.get("status") == 200
    else:
        outcome = served.get("outcome")
        answered = not served.get("is_error") and isinstance(outcome, dict) and outcome.get("refusal") is None
    assert answered, (
        f"[{anchor}, {door}] control: the twin did not serve its ordinarily served subject: {w.render(served)}"
    )
    assert _held_refusal_refused(run, twin), f"[{anchor}, {door}] CT-A (a) does not hold for this run"


def _held_refusal_cells() -> list[Any]:
    """Every (comparison, anchor, door, channel) the held-refusal deployment is judged on: the subject-keyed shape's own."""
    return [
        pytest.param(comparison, anchor, door, channel, id=f"{comparison}-{w.HELD_REFUSAL}-{anchor}-{door}-{channel}")
        for comparison in w.COMPARISONS
        for anchor in w.ANCHORS
        for door in w.DOORS
        for channel in w.channels_for(comparison=comparison, shape=w.HELD_REFUSAL, door=door)
    ]


@pytest.mark.parametrize(("comparison", "anchor", "door", "channel"), _held_refusal_cells())
def test_a_held_refusal_at_the_probe_leaves_withheld_and_nonexistent_indistinguishable(
    held_refusal_runs: w.HeldRefusalRunCache, runs: w.RunCache, comparison: str, anchor: str, door: str, channel: str
) -> None:
    """Item 4 (b), the cells: the withheld subject against the nonexistent one, by the gate's rules, CT-A (a) paired."""
    run = held_refusal_runs.get(anchor=anchor, door=door)
    twin = runs.get(shape=w.HELD_REFUSAL_TWIN, anchor=anchor, door=door)
    withheld_side, nonexistent_side, _ = w.PAIRS[comparison]
    cell = f"{comparison}, {w.HELD_REFUSAL}, {anchor}, {door}, {channel}"
    if _held_refusal_refused(run, twin):
        differing, floor, withheld, nonexistent = _compare(run, comparison=comparison, channel=channel)
        assert not differing, (
            f"SEC-020 [{cell}]: the refusal is not the same for the withheld and the nonexistent subject at"
            f" {sorted(differing)} (noise floor, not counted: {sorted(floor)})\n"
            f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
        )
        vacuous = _vacuous(twin, withheld_side, nonexistent_side)
        assert not vacuous, f"SEC-020 [{cell}]: not evidence — the twin's sides RAISED: {vacuous}"
        differing, floor, withheld, nonexistent = _compare(twin, comparison=comparison, channel=channel)
        assert not differing, (
            f"SEC-020 [{cell}]: the supported working twin tells the withheld subject apart at"
            f" {sorted(differing)} (noise floor, not counted: {sorted(floor)})\n"
            f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
        )
        return
    vacuous = _vacuous(run, withheld_side, nonexistent_side)
    assert not vacuous, (
        f"SEC-020 [{cell}]: not evidence — both sides RAISED instead of answering, and two equal exceptions"
        f" are equal on every channel: {vacuous}"
    )
    differing, floor, withheld, nonexistent = _compare(run, comparison=comparison, channel=channel)
    assert not differing, (
        f"SEC-020 [{cell}]: a withheld subject is distinguishable from a nonexistent one at {sorted(differing)}"
        f" (noise floor, not counted: {sorted(floor)})\n"
        f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
    )


# =============================================================================
# Integration (coordinator, D-IMPL-378, 2026-10-09): the floor check meets item 4 (b)'s refusal
# =============================================================================
#
# Two of Dave's 06:21 MST rulings meet here. The floor check, verbatim: "A failed spare answer cannot excuse
# differences." It accepts a floor copy that raised only where what it raised is the property the cell holds, as Q9's,
# P2 (c)'s and P6 (a)'s refusals are. Item 4 (b)'s closing-test case, verbatim: "4(b), plus the closing-test case and a
# supported working twin". Its deployment refuses every side alike with ``UnheldSubjectProbeRefused``, so its floor
# copy raises that refusal because the refusal IS the property. Merged without this, all 40 of its cells failed by
# FloorCopyDidNotAnswer (measured on the batch). ``sec020_worlds.held_refusal_is_the_property`` adds that one refusal
# under the conditions P6 (a)'s has; the three tests below hold it to them. A JUDGING CHANGE, in its own commit, for
# Dave to rule on. SEC-020 stays OPEN.


def _held_refusal_world(*, every_side_refused: bool) -> w.Run:
    """A synthetic held-refusal run: every side refused alike, or one compared side and the served side answering."""
    refusal = (
        f"{w.HELD_REFUSAL_REFUSAL}: the subject-keyed acquisition phase answered the probe identifier with a held"
        " refusal"
    )
    refused = _floor_observation({"outcome": "refused", "detail": refusal}, raised={w.ONLY: refusal})
    sides = {side: refused for side in w.HELD_REFUSAL_SIDES}
    if not every_side_refused:
        sides[w.CF_WITHHELD] = _floor_observation(_FLOOR_WITHHELD)
        sides[w.SERVED] = _floor_observation({"outcome": "served"})
    return w.Run(shape=w.HELD_REFUSAL, anchor=w.FROM_DECISION, door=w.MCP, sides=sides)


def test_control_a_held_refusal_floor_copy_is_a_floor_where_every_side_raised_it() -> None:
    """Every side of the held-refusal deployment raised item 4 (b)'s refusal with one message: the copy is a floor."""
    assert _floor_copy_did_not_answer(_held_refusal_world(every_side_refused=True), w.COUNTERFACTUAL) == {}


def test_a_held_refusal_floor_copy_excuses_nothing_where_a_side_answered() -> None:
    """A side answered: the refusal is not what the run holds, so the raised floor copy excuses nothing, by name."""
    with pytest.raises(FloorCopyDidNotAnswer):
        _require_the_floor_copy_answered(_held_refusal_world(every_side_refused=False), w.COUNTERFACTUAL)


def test_a_floor_copy_raising_the_held_refusal_in_another_shape_excuses_nothing() -> None:
    """The same refusal on every side of another shape is not item 4 (b)'s case: the floor copy excuses nothing."""
    held = _held_refusal_world(every_side_refused=True)
    other = w.Run(shape=w.SUBJECT_KEYED, anchor=held.anchor, door=held.door, sides=held.sides)
    with pytest.raises(FloorCopyDidNotAnswer):
        _require_the_floor_copy_answered(other, w.COUNTERFACTUAL)
