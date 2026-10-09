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
undeclared-population cells stay in the gate.

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
    """
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
