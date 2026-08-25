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

**What this module drives, and what it does not (finding B3).** Stated here
because the wording above claimed more than the evidence carried, and 06-20
raises the evidence where it can be raised rather than leaving the reader to
work out the gap:

* :func:`_drive` **calls the four seams directly** — ``inject_context``, then
  ``capture_effect``, then ``replay_trace``. There is
  **no harness reasoning loop** executed here, no tool-calling loop, and no
  model reached (an autouse guard fails the run if a socket opens). What is
  proven is that three adapters
  translate *one* agent definition into their own harness-native carriers
  equivalently, and report their own execution traces distinguishably. That is
  the seam claim, and it is real.
* Loop-level execution — one agent definition genuinely *running* under two
  harnesses' own loops — is **example 03's obligation in Phase 8**
  (``archive/examples/03-harness-portability``, D-06). The stronger claim is handed on
  rather than dropped.
* Every equality this module asserts has an *observed* failure mode, added by
  06-20 so that no assertion here is green for a reason unrelated to
  portability. Seam 1's has teeth on its own: the product is recovered out of
  each harness-native carrier, and an adapter that rewrote its delivered bytes
  turns the comparison red. Seam 3's and seam 4's are supplied by
  :class:`AdversarialAdapter`, a conforming wrapper that delegates every seam to
  a real adapter and perturbs exactly one value crossing it.
* **The limit of what that adversarial leg buys, plainly:** all three shipped
  adapters' ``capture_effect`` remain delegations to
  :meth:`~ccf.agents.agent.Agent.emit_effect`, so the honest three-leg emission
  equality still cannot fail. The adversarial leg proves the assertion is
  sensitive to perturbation, not that the three adapters are independent
  implementations. Read the honest emission equality as "the fabric, not the
  harness, decides what an effect is" — which is the governed-emission claim CCF
  actually wants — and not as three independent implementations agreeing.

The polished ``archive/examples/03-harness-portability`` directory with its README is
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
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest

from ccf.agents.agent import Agent, EmittedEffect
from ccf.agents.definitions import AgentDefinition
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.harness.protocol import (
    EffectCapability,
    EffectRefusal,
    HarnessAdapterProtocol,
    HarnessCapabilities,
)
from ccf.products.contract import ContextProductContract
from ccf.projection.plan import Perspective
from ccf.replay.record import (
    NO_HARNESS,
    NO_HARNESS_TRACE,
    DecisionReplayRecord,
    HarnessTrace,
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
    _agent_fixture,
    _carrier_strings,
    _execution,
    _grants_fixture,
    _harness_fixture,
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


# --- the adversarial leg: a failure mode for the axes that had none -----------


class AdversarialAdapter:
    """A conforming adapter that delegates every seam and corrupts exactly one value.

    Added by 06-20 to close finding B3's evidence half. Two of this module's
    equalities were green for a reason unrelated to portability: seam 3 because
    all three shipped adapters delegate ``capture_effect`` to
    :meth:`~ccf.agents.agent.Agent.emit_effect`, and seam 4's per-harness
    difference because nothing perturbed a reported trace. An assertion that
    cannot fail is not evidence, so this supplies the failure.

    It is a **wrapper, not a fork**: every seam delegates to a real adapter
    obtained from a real :class:`HarnessLeg`, and the perturbation is applied to
    the value crossing the seam. No shipped adapter code is edited, and the
    corrupted value is observed by the same :func:`_drive` the honest legs go
    through — which is the point, because a bespoke assertion written beside this
    class would prove something about the assertion rather than about ``_drive``.

    It satisfies :class:`~ccf.harness.protocol.HarnessAdapterProtocol`
    structurally rather than shadowing it; the conformance suite's own
    ``isinstance`` check is asserted below on an instance of this class, so a
    wrapper that had drifted off the Protocol could not quietly pass as one.

    Exactly one perturbation is applied per instance, by construction of the
    tests that build it: a wrapper corrupting two seams at once would leave which
    assertion actually fired ambiguous.
    """

    def __init__(
        self,
        inner: HarnessAdapterProtocol,
        *,
        payload_extra: Mapping[str, Any] | None = None,
        trace_update: Mapping[str, Any] | None = None,
        drop_trace: bool = False,
    ) -> None:
        self._inner = inner
        self._payload_extra: Mapping[str, Any] = dict(payload_extra or {})
        self._trace_update: Mapping[str, Any] = dict(trace_update or {})
        self._drop_trace = drop_trace

    def capabilities(self) -> HarnessCapabilities:
        """Delegated verbatim — the wrapper impersonates the harness it wraps."""
        return self._inner.capabilities()

    def inject_context(
        self,
        *,
        agent: Agent,
        products: tuple[ContextProductContract, ...],
        instructions: tuple[str, ...],
    ) -> object:
        """Seam 1, untouched: the consumption axis already has teeth (B3)."""
        return self._inner.inject_context(
            agent=agent, products=products, instructions=instructions
        )

    def expose_skills(self, *, agent: Agent) -> tuple[str, ...]:
        return self._inner.expose_skills(agent=agent)

    def capture_effect(
        self, *, agent: Agent, output: Mapping[str, Any]
    ) -> EmittedEffect | EffectRefusal:
        """Seam 3, with the payload perturbed on the way into the real adapter.

        The perturbation is on the *input* to the governed emission rather than
        on its result, which is what makes this a model of a misbehaving harness
        binding instead of a tampered record: the real ``emit_effect`` runs, and
        the effect it produces is honestly derived from the corrupted output.
        """
        return self._inner.capture_effect(
            agent=agent, output={**dict(output), **dict(self._payload_extra)}
        )

    def replay_trace(self, *, execution: object) -> HarnessTrace:
        """Seam 4, reporting either a perturbed block or a dropped one.

        ``drop_trace`` returns the :data:`~ccf.replay.record.NO_HARNESS_TRACE`
        sentinel — a harness that ran and reported nothing, which by value is
        indistinguishable from an honest no-harness decision. That
        indistinguishability is the threat (T-06-88), and it is why the trace
        assertion below asserts liveness rather than reading absence.
        """
        trace = self._inner.replay_trace(execution=execution)
        if self._drop_trace:
            return NO_HARNESS_TRACE
        if self._trace_update:
            return trace.model_copy(update=dict(self._trace_update))
        return trace


def _adversarial_leg(
    leg: HarnessLeg,
    *,
    payload_extra: Mapping[str, Any] | None = None,
    trace_update: Mapping[str, Any] | None = None,
    drop_trace: bool = False,
) -> HarnessLeg:
    """A real leg with its adapter factory wrapped in :class:`AdversarialAdapter`.

    Everything else on the leg — the execution builder, the reported values, the
    refusal driver — is the real leg's, so the adversarial run differs from the
    honest one in the perturbation and nothing else.
    """

    def adapter(capability: EffectCapability) -> HarnessAdapterProtocol:
        return AdversarialAdapter(
            leg.adapter(capability),
            payload_extra=payload_extra,
            trace_update=trace_update,
            drop_trace=drop_trace,
        )

    return leg._replace(adapter=adapter)


def _corrupt_payload() -> Mapping[str, Any]:
    """The seam-3 perturbation, drawn from the banking fixtures (CINV-01).

    The granted skill's own argument mapping, merged into the emitted payload.
    A value authored here would be a domain value in test code; this is the
    fixtures' own vocabulary used somewhere it does not belong, which is exactly
    the shape of the corruption being modelled.

    Asserted disjoint from the payload's keys, because a "perturbation" that
    merged a mapping the payload already carried would be an identity and the
    inversion built on it would pass by accident.
    """
    arguments = dict(_agent_fixture()["slice"]["granted_skill"]["arguments"])
    payload = dict(_agent_fixture()["slice"]["effect_payload"])
    assert arguments, "the fixture supplies no perturbation material"
    assert not set(arguments) & set(payload), (
        "the seam-3 perturbation overlaps the payload it perturbs, so merging it"
        " may be an identity — the inversion below would then pass vacuously"
    )
    return arguments


def test_the_adversarial_leg_is_a_conforming_adapter_not_a_double(
    legs: tuple[HarnessLeg, ...],
) -> None:
    """The perturbation is observed through the Protocol, not around it.

    A wrapper that had drifted off :class:`HarnessAdapterProtocol` would still
    make the inversions below fail — for the wrong reason. This pins that the
    corrupted value crosses the same declared surface the honest legs cross, and
    that the wrapper reports the wrapped harness's own declared capabilities
    rather than a claim of its own.
    """
    inner = legs[0].adapter("governed")
    wrapped = _adversarial_leg(legs[0], payload_extra=_corrupt_payload()).adapter(
        "governed"
    )
    assert isinstance(wrapped, AdversarialAdapter)
    assert isinstance(wrapped, HarnessAdapterProtocol)
    assert wrapped.capabilities() == inner.capabilities()


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


def _assert_the_trace_is_the_harness_own(leg: HarnessLeg, run: Run) -> None:
    """The recorded harness block is the one *this* harness reported.

    Factored out and strengthened by 06-20 (finding B3). The pre-existing
    assertion checked that the block was non-sentinel and per-harness distinct,
    which a harness reporting a plausible block belonging to some other
    deployment would satisfy. So the values are compared against the leg's **own**
    declared ``reported_model`` and ``trace_id`` — the fixtures' statement of what
    that harness reports, which is what
    ``test_harness_adapter.py::test_seam_4_records_what_the_harness_reported``
    already compares at the single-leg bar. Sharing that bar here is what gives
    the axis a failure mode a wrapper can trip.

    Liveness rather than absence-reading is deliberate (T-06-88): a dropped block
    equals :data:`~ccf.replay.record.NO_HARNESS_TRACE`, which is also what an
    honest no-harness decision carries, so the sentinel can never distinguish the
    two. Only "this harness ran, so it must name itself" can.
    """
    trace = run.record.model_version.harness_trace
    assert trace != NO_HARNESS_TRACE, (
        f"{leg.harness_id} reported no harness block at all, which is byte-identical"
        " to an honest fabric-direct decision — a dropped trace and an absent one"
        " must not be the same artifact (T-06-88, T-06-63)"
    )
    assert trace.harness_id == leg.harness_id != NO_HARNESS
    assert leg.reported_model in trace.model_version, (
        f"{leg.harness_id}'s recorded harness block does not carry the model its"
        f" harness reported ({leg.reported_model!r} not in"
        f" {trace.model_version!r}) — dimension 3's harness half is then a claim"
        " no run made (T-06-87)"
    )
    assert trace.trace_id == leg.trace_id != NO_HARNESS
    assert trace.input_tokens > 0 and trace.output_tokens > 0


def _foreign_trace_values(leg: HarnessLeg) -> Mapping[str, Any]:
    """The seam-4 perturbation: another deployment's reported values (CINV-01).

    Drawn from the same ``harnesses.yaml`` block set the honest legs read, but
    from a *different* harness's block — the most realistic corruption available,
    because every value is one some harness genuinely does report, so the block
    stays structurally plausible and only its attribution is wrong. A literal
    authored here would be a deployment value in test code (§6.4) and, worse, an
    obviously-invalid one that a weaker assertion could reject for the wrong
    reason.

    Asserted to actually differ from the leg's own reported model, so the
    perturbation cannot be an identity.
    """
    for param in HARNESS_PARAMS:
        values = _harness_fixture()[param]
        if values["reported_model"] != leg.reported_model:
            foreign = {
                "model_version": values["reported_model"],
                "input_tokens": values["input_tokens"],
                "output_tokens": values["output_tokens"],
            }
            assert foreign["model_version"] != leg.reported_model
            return foreign
    raise AssertionError(
        "every harness fixture block reports the same model, so no foreign trace"
        " value exists to perturb with — the fixtures deliberately differ per"
        " harness and this suite depends on it"
    )


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

    for leg, run in zip(legs, runs, strict=True):
        assert run.harness_id == leg.harness_id
        _assert_the_trace_is_the_harness_own(leg, run)

    assert len({canonical_bytes(trace) for trace in traces.values()}) == 3
    assert HARNESS_ATTRIBUTABLE not in _governed_fields(runs[0].record)
    assert all(
        f"model_version.{HARNESS_ATTRIBUTABLE}" not in _governed_fields(run.record)
        for run in runs
    )


def test_a_leg_that_corrupted_its_reported_trace_is_detected(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """B3's evidence half for seam 4: the trace axis has a failure mode too.

    Both halves of D-IMPL-55's split are asserted at once, which is the only way
    the split is shown to be doing work: the governed comparison **still passes**
    over the corrupted leg, because harness-attributable values are excluded by
    name and a corrupt harness therefore cannot reach a field CCF governs
    (T-06-89); and the trace assertion **fails**, because the block it reports is
    not the block its harness reported (T-06-87).

    A corruption that had also moved a governed field would prove the opposite of
    what this module claims, so the first assertion is as load-bearing as the
    second.
    """
    leg = legs[0]
    adversarial = _adversarial_leg(leg, trace_update=_foreign_trace_values(leg))
    runs = _drive_all((*legs, adversarial), world, second_agent=False)
    honest, corrupted = runs[0], runs[-1]

    # The corruption stayed inside the harness block.
    assert _governed_fields(corrupted.record) == _governed_fields(honest.record)

    # And the harness block itself gives it away.
    _assert_the_trace_is_the_harness_own(leg, honest)
    with pytest.raises(AssertionError, match="the model its harness reported"):
        _assert_the_trace_is_the_harness_own(leg, corrupted)
    assert canonical_bytes(
        corrupted.record.model_version.harness_trace
    ) != canonical_bytes(honest.record.model_version.harness_trace)


def test_a_dropped_harness_trace_is_caught_by_liveness_not_by_absence(
    legs: tuple[HarnessLeg, ...], world: World
) -> None:
    """T-06-88: a harness that ran and reported nothing must not read as honest.

    The sentinel case, asserted rather than assumed. A dropped trace is **by
    value** exactly :data:`~ccf.replay.record.NO_HARNESS_TRACE` — the same block a
    fabric-direct decision carries — so no comparison against the sentinel can
    tell a repudiating harness from an honest no-harness run. That is why the
    assertion is *liveness*: this harness ran, so its block must name it.

    Asserted in both directions, because the sentinel equality on its own would
    look identical under a suite that had stopped checking liveness at all.
    """
    leg = legs[0]
    runs = _drive_all((*legs, _adversarial_leg(leg, drop_trace=True)), world, second_agent=False)
    dropped = runs[-1].record.model_version.harness_trace

    assert dropped == NO_HARNESS_TRACE
    assert dropped.harness_id == NO_HARNESS
    assert dropped.input_tokens == dropped.output_tokens == 0

    _assert_the_trace_is_the_harness_own(leg, runs[0])
    with pytest.raises(AssertionError, match="reported no harness block"):
        _assert_the_trace_is_the_harness_own(leg, runs[-1])


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
