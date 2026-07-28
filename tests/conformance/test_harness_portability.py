"""The harness-neutrality proof: one agent definition, three harnesses (XPRC-03).

CLAUDE.md §7.3 says *portability is demonstrated, not asserted*, and mission
success condition 3 rests on the demonstration. This module is it, for I.3: a
single agent definition artifact — **the same artifact, loaded once, producing
one** :class:`~ccf.agents.agent.Agent` **object** — is handed to all three
D-IMPL-24 reference adapters, and what comes back is compared on two axes:

* **What the harness consumed.** The Context Product each adapter delivered to
  its harness's context surface, recovered *out of the harness-native carrier*
  and compared byte for byte across the three. Recovered rather than assumed:
  an assertion that the product the test already holds equals itself would pass
  under an adapter that delivered something else entirely, and 06-14 found a
  live instance of exactly that failure mode — ADK interpolates a ``str``
  instruction against session state, so a product bound the obvious way would
  have had its own braces rewritten while every naive assertion stayed green.
* **What CCF governs about the decision.** The five-dimension Decision Replay
  record, compared field by field with D-18's split: exact equality on every
  governed field, and *isolation* rather than equality for
  ``model_version.harness_trace``, which is where harness-attributable values
  are confined. Full byte equality across three different SDKs would either
  fail always or force the attribution out of the record entirely, so D-18
  draws the line and this module holds it from both sides — a governed field
  that diverged names itself, and a ``harness_trace`` that did *not* differ per
  harness fails too.

**Why the records are not equal by construction.** The cheap version of this
test builds one record, copies it three times with a different trace, and
declares equality. That proves nothing. Here each harness's record is built
from *that harness's own run*: dimension 5's ``product_content_address`` is
derived from the product recovered from that adapter's carrier, dimension 4 is
the conditioning the agent serialized for that run, and dimension 3's harness
block comes from a real execution driven through that harness's own machinery.
An adapter that corrupted the product it delivered — the ADK hazard above —
moves ``product_content_address`` and the comparison goes red naming that
field.

**D-23, the second agent.** Everything above is also run for a *different*
agent definition with a different grant set, and its governed field set is
asserted **distinct** from the first agent's. Without it, a comparison that
collapsed every record to a constant would pass the whole module.

The polished ``examples/03-harness-portability`` directory with its README is
Phase 8 scope (D-06). This is the I.3 precursor, and it ships as conformance
rather than as an example so the claim is in CI from the wave it was made.

Everything domain-specific — the agent definitions, the policy regimes, the
grants, the product classes, the per-harness deployment values — comes from
``tests/fixtures/banking``. This module holds mechanism only (CLAUDE.md §6.4),
and it names no harness SDK type: the three legs, the carrier walk, and the
skip mechanism are all shared with ``test_harness_adapter.py`` rather than
re-implemented at a lower bar.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any

import pytest

from ccf.agents.agent import Agent, EmittedEffect
from ccf.agents.definitions import AgentDefinition
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.contract import ContextProductContract
from ccf.projection.plan import Perspective
from ccf.replay.record import (
    NO_HARNESS,
    DecisionReplayRecord,
    ModelVersionRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.skills.grants import SkillGrant

from conformance.test_harness_adapter import (
    BOUNDARY,
    HARNESS_PARAMS,
    HarnessLeg,
    World,
    _carrier_strings,
    _execution,
    _grants_fixture,
    _product,
    build_harness_leg,
)

pytestmark = [pytest.mark.conformance, pytest.mark.harness]


# --- what the comparison governs ----------------------------------------------

#: Top-level record fields D-18 governs — every dimension except the one that
#: carries the harness block. Compared for exact equality across all three
#: harnesses, by canonical serialization.
GOVERNED_DIMENSIONS = (
    "context_fabric_snapshot",
    "policy_bindings",
    "perspective_conditioning",
    "content_generation_path",
)

#: Dimension 3's own governed fields. Dimension 3 is split: the fabric records
#: what *it* invoked in these, and the harness records what *it* invoked in
#: ``harness_trace``. Conflating the two is precisely how a harness overwrites a
#: governed claim (T-06-62).
GOVERNED_MODEL_VERSION_FIELDS = ("assembly_mode", "model_version")

#: Dimension 3's harness-attributable sub-structure — excluded from the
#: governed comparison and asserted to *differ* per harness instead (D-18, D-25).
HARNESS_ATTRIBUTABLE = "harness_trace"

#: Record fields that are record metadata rather than a replay dimension.
#: Named so the classification below is exhaustive over
#: :class:`~ccf.replay.record.DecisionReplayRecord` and a future field cannot
#: land in neither bucket.
RECORD_METADATA = ("tenant_id", "recorded_at")

#: Segments of the harness identities that are CCF's own vocabulary and so
#: cannot be evidence that a definition named a harness. ``agent`` and ``sdk``
#: appear throughout the fabric's own naming; asserting their absence from an
#: agent definition would be asserting something false rather than something
#: strong (CLAUDE.md §6.5 is about *harness* names).
GENERIC_SEGMENTS = frozenset({"agent", "sdk"})

#: The harness module names the adapters import — the other half of "names no
#: harness", alongside the harness ids the adapters declare.
HARNESS_MODULES = ("claude_agent_sdk", "google.adk", "langgraph")


# --- the guards this module's evidence depends on -----------------------------


@pytest.fixture(autouse=True)
def no_model_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the run if anything opens a socket (D-09, T-06-72).

    Re-declared rather than imported: an autouse fixture applies to the module
    that declares it, so the portability runs would otherwise be the one place
    in the phase where a model call could happen unnoticed.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "the harness portability proof attempted network egress; it must"
            " drive SDK objects in-process with no model (D-09)"
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_the_no_model_guard_is_actually_installed() -> None:
    """The guard is only evidence if it fires."""
    with pytest.raises(AssertionError, match="network egress"):
        socket.create_connection(("127.0.0.1", 9))


@pytest.fixture
def legs() -> tuple[HarnessLeg, ...]:
    """All three D-IMPL-24 legs at once — which is what portability *is*.

    Built from the conformance suite's own :data:`HARNESS_PARAMS` and its own
    builder, so a harness that joins the adapter bar joins this proof in the
    same commit or fails here.
    """
    return tuple(build_harness_leg(param) for param in HARNESS_PARAMS)


def test_the_proof_drives_every_harness_the_conformance_bar_drives(
    legs: tuple[HarnessLeg, ...],
) -> None:
    """A portability claim over a subset of the adapters is not the claim."""
    assert len(legs) == len(HARNESS_PARAMS) == 3
    assert len({leg.harness_id for leg in legs}) == 3


# --- one agent, three harnesses -----------------------------------------------


def _delivered_products(carrier: object) -> tuple[bytes, ...]:
    """Every Context Product document reachable on a harness's context surface.

    Recovers the product from the carrier the way a *harness* would meet it:
    by finding JSON documents inside the strings the adapter placed there. One
    adapter hands the harness the product as its own carried string, another
    joins it into a single system prompt, a third hands over a callable that
    will produce one — so nothing here may assume a shape, and this walks the
    same generic ``_carrier_strings`` probe the conformance suite uses.

    ``raw_decode`` from each ``{`` is what makes the joined case work: the
    product is embedded in a larger string, and this lifts exactly the
    document back out. A document that had been interpolated, truncated, or
    re-serialized would either fail to parse or parse to different bytes, which
    is the failure this recovery exists to be able to see.
    """
    decoder = json.JSONDecoder()
    found: list[bytes] = []
    for text in _carrier_strings(carrier):
        for index, character in enumerate(text):
            if character != "{":
                continue
            try:
                document, end = decoder.raw_decode(text, index)
            except ValueError:
                continue
            if isinstance(document, dict) and "schema_name" in document:
                found.append(text[index:end].encode("utf-8"))
    return tuple(dict.fromkeys(found))


@dataclass(frozen=True)
class Run:
    """One agent, run under one harness, and everything it is judged on."""

    harness_id: str
    delivered_product: bytes
    record: DecisionReplayRecord
    emission_address: str


def _drive(
    leg: HarnessLeg,
    world: World,
    *,
    agent: Agent,
    definition: AgentDefinition,
    product: ContextProductContract,
    instructions: tuple[str, ...],
) -> Run:
    """Run the same fabric-side operation under one harness, through its adapter.

    Every value the resulting :class:`Run` is judged on is derived from *this*
    harness's own pass through the seams — the product is recovered from the
    carrier seam 1 built, the harness block from a real execution driven
    through seam 4, the emission from seam 3. Nothing is copied in from a
    shared record, which is what stops the equality below from being an
    identity.
    """
    adapter = leg.adapter("governed")

    # Seam 1 — and the product comes back out of the carrier, not off the shelf.
    carrier = adapter.inject_context(
        agent=agent, products=(product,), instructions=instructions
    )
    delivered = _delivered_products(carrier)
    assert len(delivered) == 1, (
        f"{leg.harness_id} delivered {len(delivered)} recoverable Context"
        " Product documents to its context surface, not exactly one — the"
        " bytes the replay record attests are not the bytes the harness saw"
    )
    recovered = ContextProductContract.model_validate_json(delivered[0])

    # Seam 3 — the governed emission, as this adapter produced it.
    emitted = adapter.capture_effect(agent=agent, output=dict(product.payload))
    assert isinstance(emitted, EmittedEffect)

    # Seam 4 — what this harness reported, from a real execution.
    trace = adapter.replay_trace(execution=leg.execution())

    record = build_replay_record(
        execution=_execution(definition),
        product=recovered,
        perspective=Perspective(
            principal_id=world.actor, role=definition.perspective.role
        ),
        policy_bindings=(
            PolicyBinding(key="policy.bundle", version=definition.policy_regime.ref),
        ),
        assembly_mode="algorithmic",
        recorded_at=BOUNDARY,
        agent_conditioning=agent.perspective_conditioning(
            principal_id=world.actor,
            grant_set_hash=world.ledger.grant_set_hash(agent.identity.definition_hash),
        ),
        harness_trace=trace,
    )
    return Run(
        harness_id=leg.harness_id,
        delivered_product=delivered[0],
        record=record,
        emission_address=content_hash(emitted),
    )


def _governed_fields(record: DecisionReplayRecord) -> dict[str, bytes]:
    """Every field D-18 governs, canonically serialized, keyed by name.

    Canonical serialization rather than ``model_dump()``: the repo's canonical
    serializer normalizes field by field precisely because dumping rebuilds
    set-valued fields as sets of dicts, which makes lineage claims unhashable
    and comparisons quietly wrong (T-06-90, an I.1 finding).

    Keyed by name so a divergence *names itself* — a bare "the records differ"
    is not an actionable failure for a claim this load-bearing.
    """
    governed = {
        name: canonical_bytes(getattr(record, name)) for name in GOVERNED_DIMENSIONS
    }
    governed.update(
        {
            f"model_version.{name}": canonical_bytes(
                getattr(record.model_version, name)
            )
            for name in GOVERNED_MODEL_VERSION_FIELDS
        }
    )
    governed["tenant_id"] = canonical_bytes(record.tenant_id)
    return governed


def _drive_all(
    legs: tuple[HarnessLeg, ...], world: World, *, second_agent: bool
) -> tuple[Run, ...]:
    """One agent definition, every harness. The construction site is singular.

    The agent object is built once by :class:`World` from one artifact and the
    *same object* is handed to each adapter — asserted below rather than
    described, because three near-identical fixtures that happened to agree
    would satisfy a looser reading of "unmodified" while proving nothing about
    the definition being portable.
    """
    if second_agent:
        agent, definition, grant = world.agent_b, world.definition_b, world.grant_b
        instructions: tuple[str, ...] = ()
    else:
        agent, definition, grant = world.agent_a, world.definition_a, world.grant_a
        instructions = world.instructions()

    world.bind(grant, definition)
    product = agent.consume(_product(definition), now=BOUNDARY)
    runs = tuple(
        _drive(
            leg,
            world,
            agent=agent,
            definition=definition,
            product=product,
            instructions=instructions,
        )
        for leg in legs
    )
    # One object, three adapters — the literal reading of "unmodified".
    assert all(
        run.record.perspective_conditioning.agent_definition_hash
        == agent.identity.definition_hash
        for run in runs
    )
    return runs


@pytest.fixture
def world() -> World:
    return World()


# --- the definition names no harness (CLAUDE.md §6.5) -------------------------


def test_the_agent_definition_names_no_harness(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """A definition that named a harness would make the whole claim circular.

    The forbidden tokens are *derived* from what the adapters actually declare
    and import — the three ``harness_id`` values and the three harness module
    names — rather than authored here, so a fourth adapter cannot arrive with a
    vendor name this test never heard of. The check is over the definitions'
    canonical bytes rather than the YAML file text: the bytes are what the
    factory consumed, and a comment in a fixture file is not something the
    agent carries.
    """
    segments = {
        segment
        for identity in (*(leg.harness_id for leg in legs), *HARNESS_MODULES)
        for segment in identity.replace(".", "-").replace("_", "-").split("-")
    }
    forbidden = {segment for segment in segments if segment not in GENERIC_SEGMENTS}
    assert {"claude", "adk", "langgraph", "google"} <= forbidden

    for definition in (world.definition_a, world.definition_b):
        carried = canonical_bytes(definition).decode("utf-8").lower()
        for token in sorted(forbidden):
            assert token not in carried, (
                f"the agent definition {definition.name!r} names {token!r} —"
                " harness binding happens at runtime through the adapter, never"
                " in the definition (CLAUDE.md §6.5)"
            )


# --- the Context Product each harness consumed --------------------------------


def test_the_consumed_product_is_byte_identical_across_the_three_harnesses(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """The bytes the harness saw, recovered from each carrier, are the same bytes.

    Compared across harnesses, not against the product the test holds: the
    cross-harness comparison is the portability claim, and it is the one an
    adapter that quietly rewrote what it delivered cannot satisfy.
    """
    runs = _drive_all(legs, world, second_agent=False)
    delivered = {run.harness_id: run.delivered_product for run in runs}
    assert len(set(delivered.values())) == 1, (
        "the three adapters delivered different Context Product bytes:"
        f" { {name: len(value) for name, value in delivered.items()} }"
    )
    # And what they delivered is what the fabric admitted, unaltered.
    product = world.agent_a.consume(_product(world.definition_a), now=BOUNDARY)
    assert set(delivered.values()) == {canonical_bytes(product)}


def _assert_one_governed_emission(runs: tuple[Run, ...]) -> None:
    """Seam 3's cross-leg equality, in exactly one place so it can be inverted.

    Factored out by 06-20 (finding B3) rather than left inline: the adversarial
    case below has to fail *this* assertion, and an inversion that re-spelled the
    comparison beside the wrapper would prove something about the re-spelling.

    Addresses are collected as a tuple rather than keyed by harness id, because
    an adversarial leg wraps a real adapter and therefore reports that adapter's
    ``harness_id`` — keying would collapse the very pair being compared.
    """
    addresses = tuple(run.emission_address for run in runs)
    assert len(set(addresses)) == 1, (
        "the legs produced different governed emissions:"
        f" { {run.harness_id: run.emission_address for run in runs} }"
    )


def test_the_governed_emission_is_identical_across_the_three_harnesses(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """Seam 3's typed value is the agent's, so three harnesses produce one effect."""
    _assert_one_governed_emission(_drive_all(legs, world, second_agent=False))


def test_a_leg_that_corrupted_the_governed_emission_turns_the_equality_red(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """B3's evidence half for seam 3: the equality has an observed failure mode.

    The assertion above is structurally guaranteed over the three *shipped*
    adapters — all three delegate ``capture_effect`` to
    :meth:`~ccf.agents.agent.Agent.emit_effect`, so feeding one payload three
    times must hash-equal. That makes it green for a reason unrelated to
    portability, and B3 is right that a green assertion which cannot fail is not
    evidence. This is the failure mode: a fourth leg that delegates every seam to
    a real adapter and perturbs only the value handed through seam 3.

    Driven through :func:`_drive` like every other leg, so the corruption is
    observed by the same code path the honest legs use rather than by a bespoke
    assertion written beside the wrapper.
    """
    adversarial = _adversarial_leg(legs[0], payload_extra=_corrupt_payload())
    runs = _drive_all((*legs, adversarial), world, second_agent=False)

    with pytest.raises(AssertionError, match="different governed emissions"):
        _assert_one_governed_emission(runs)

    # The perturbed leg is the *only* reason it failed: the honest three still agree.
    honest = runs[: len(legs)]
    _assert_one_governed_emission(honest)
    assert runs[-1].emission_address not in {run.emission_address for run in honest}


def test_the_adversarial_leg_is_inert_when_its_perturbation_is_removed(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """The inversion's inversion: a pure delegate must leave the suite green.

    Without this, the case above would pass equally well against a wrapper that
    broke the run for some reason other than the perturbation — a leg that failed
    to inject context, or one whose delegation dropped the agent. The same
    wrapper, the same four-leg drive, the perturbation withheld.
    """
    _assert_one_governed_emission(
        _drive_all((*legs, _adversarial_leg(legs[0])), world, second_agent=False)
    )


# --- D-18: governed equality, harness-attributable isolation ------------------


def test_the_governed_replay_fields_are_exactly_equal_across_harnesses(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """D-18's first half, field by field, with the divergent field named."""
    runs = _drive_all(legs, world, second_agent=False)
    reference, *others = runs
    expected = _governed_fields(reference.record)
    for run in others:
        actual = _governed_fields(run.record)
        assert set(actual) == set(expected)
        for name in sorted(expected):
            assert actual[name] == expected[name], (
                f"governed replay field {name!r} diverged between"
                f" {reference.harness_id} and {run.harness_id}: a"
                " harness-attributable value reached a field CCF governs"
                " (D-18, T-06-86)"
            )


def test_the_governed_field_set_is_exhaustive_over_the_record(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """Every record field is classified — governed, harness, or metadata.

    Structural rather than textual: a dimension added later, or a field added
    to dimension 3, lands in no bucket and fails here rather than being
    silently excluded from a comparison that still reports success.
    """
    assert set(DecisionReplayRecord.model_fields) == {
        *GOVERNED_DIMENSIONS,
        *RECORD_METADATA,
        "model_version",
    }
    assert set(ModelVersionRecord.model_fields) == {
        *GOVERNED_MODEL_VERSION_FIELDS,
        HARNESS_ATTRIBUTABLE,
    }


def test_the_harness_trace_is_isolated_and_differs_per_harness(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """D-18's second half: excluded from equality, and asserted to differ.

    Both failure directions are loud. A trace identical across the three, or an
    empty one, fails here rather than passing on absence — which is what an
    "equivalent records" test without this assertion would do.
    """
    runs = _drive_all(legs, world, second_agent=False)
    traces = {run.harness_id: run.record.model_version.harness_trace for run in runs}
    assert len(traces) == 3

    for harness_id, trace in traces.items():
        assert trace.harness_id == harness_id
        assert trace.harness_id != NO_HARNESS
        assert trace.model_version != NO_HARNESS
        assert trace.trace_id != NO_HARNESS
        assert trace.input_tokens > 0 and trace.output_tokens > 0

    assert len({canonical_bytes(trace) for trace in traces.values()}) == 3
    assert HARNESS_ATTRIBUTABLE not in _governed_fields(runs[0].record)
    assert all(
        f"model_version.{HARNESS_ATTRIBUTABLE}" not in _governed_fields(run.record)
        for run in runs
    )


def test_a_live_record_still_carries_exactly_five_dimensions(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """INV-CH7-80 on the records this proof actually produced (T-06-89).

    Counted on a live record rather than on the class, so a ``harness_trace``
    promoted to a sixth top-level block fails here as well as in
    ``tests/replay/``. Dimensions are the fields whose value is itself a typed
    contract; the two metadata fields are scalars and are excluded by shape,
    not by name.
    """
    runs = _drive_all(legs, world, second_agent=False)
    for run in runs:
        dimensions = [
            name
            for name in DecisionReplayRecord.model_fields
            if isinstance(getattr(run.record, name), CCFContract)
        ]
        assert len(dimensions) == 5, dimensions
        assert set(dimensions) == {*GOVERNED_DIMENSIONS, "model_version"}


# --- D-23: the equivalence is per-agent, not a constant ----------------------


def test_two_agents_each_equal_across_harnesses_and_distinct_from_each_other(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """D-23: without a second agent, a collapsing comparison passes everything.

    The second definition is a different agent under a different policy regime
    with a different grant, so its governed field set must differ — and the
    two fields that carry *which agent, which skills* must differ specifically,
    because a comparison that agreed on those would have stopped distinguishing
    agents at all (T-06-87).
    """
    first = _drive_all(legs, world, second_agent=False)
    second = _drive_all(legs, world, second_agent=True)

    # Each agent's three records agree with themselves.
    for runs in (first, second):
        fields = [_governed_fields(run.record) for run in runs]
        assert fields[0] == fields[1] == fields[2]

    # And the two agents do not agree with each other.
    assert _governed_fields(first[0].record) != _governed_fields(second[0].record)

    conditioning = tuple(
        run.record.perspective_conditioning for run in (first[0], second[0])
    )
    assert conditioning[0].agent_definition_hash != conditioning[1].agent_definition_hash
    assert conditioning[0].grant_set_hash != conditioning[1].grant_set_hash
    assert conditioning[0].grant_set_hash and conditioning[1].grant_set_hash

    # The distinct grants are the fixtures' own, not something derived here.
    grants: tuple[SkillGrant, ...] = (world.grant_a, world.grant_b)
    assert grants[0].skill_name != grants[1].skill_name
    assert _grants_fixture()["clock"]["start"]
