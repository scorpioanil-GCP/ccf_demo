"""A deployment-declared demonstration serve instant, and why it cannot leak (`D-IMPL-378` C1).

**SDK-defined** (CLAUDE.md §11; ruling C1 (a), Dave, 2026-10-07/08): *"an SDK way
for a deployment to declare a fixed demonstration serve instant, honored by both
transports, never usable in production (security review required)"*. How it is
kept out of production was ruled option (b) (Dave, 2026-10-08 10:50 MST); these
tests hold it: the declaration is refused outside the SDK's development
substrates, and every record made under it pins it.

What each test asserts, by mechanism:

* the declared instant IS the serve instant (``served_at``) on the in-process
  transport, and ``as_of=None`` resolves to it — on both transports' clients;
* a question cannot move it — ``served_at`` stays the declared instant whatever
  the question asks as of;
* a composition that composes its own clock beside a declaration is refused by
  name (``DemonstrationServeInstantConflict``), on the resolver and on the stdio
  client — never a silent winner;
* a declaration registered AFTER a resolver was built does not reach it;
* every record written under the declaration — served AND refused — pins the
  declaration's exact ``(key, version)`` in dimension 2;
* the production guard refuses a declaration over a non-development graph
  substrate and over a non-file artifact store
  (``DemonstrationServeInstantRefused``, by reason);
* the erasure consult keeps the composition's own clock (the declared instant is
  confined to the serve clock).

The deployment is the client suite's committed fixture, copied per test and
seeded BEFORE the declaration is appended, so a base tree that cannot parse the
section fails inside each test rather than erroring in a fixture.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.client.adapters.binding_document import load_binding_document
from ccf.client.adapters.inprocess import InProcessAdapter, _boot
from ccf.client.adapters.mcp_stdio import McpStdioAdapter
from ccf.client.codec import DecodedOutcome, decode_outcome
from ccf.client.wire import WireRequest
from ccf.contracts.canonical import content_hash
from ccf.graph.registry import AdapterPin
from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord, PolicyBinding

from tests.client.conftest import SEEDED_AT, config_document
from tests.client.fixtures import STDIO_SERVER
from tests.composition import register_typed_at_composition

#: The instant the deployment declares it serves at: five minutes after the
#: fixture's rows were observed and its pinned question asks as of, inside the
#: fixture product's declared lifetime (``product_ttl_seconds: 600``), so a serve
#: at this instant is live and a serve at today's date is expired.
DECLARED = datetime(2026, 3, 2, 12, 5, tzinfo=UTC)

#: A question instant DIFFERENT from the declared serve instant, still inside the
#: answer's lifetime as served at :data:`DECLARED`.
OTHER_QUESTION = datetime(2026, 3, 2, 12, 3, tzinfo=UTC)

#: A clock a composition might compose for itself.
COMPOSED = datetime(2026, 3, 2, 12, 1, tzinfo=UTC)

#: The SDK's artifact class id for the declaration, spelled once here so every
#: assertion about the record names the same key the SDK derives.
CLASS_ID = "ccf.demonstration-serve-instant"


def declare(root: Path, instant: datetime = DECLARED) -> None:
    """Append the ``demonstration_serve_instant:`` section to the copy's config."""
    config = root / "ccf_config.yaml"
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text
        + "\n# D-IMPL-378 C1: this copy serves as of a declared demonstration instant.\n"
        + "demonstration_serve_instant:\n"
        + f'  serve_instant: "{instant.isoformat()}"\n',
        encoding="utf-8",
    )


def request_for(root: Path, *, as_of: datetime | None) -> WireRequest:
    """The fixture's one declared question, with the threshold its contract requires."""
    config = config_document(root)
    required = config["request_contract"]["arguments"]["required"]
    assert len(required) == 1, required
    return WireRequest(
        product_id=str(config["product_class"]["schema_name"]),
        parameters={str(required[0]): 20},
        temporal_boundary=as_of,
    )


def ask(adapter: InProcessAdapter, root: Path, *, as_of: datetime | None) -> DecodedOutcome:
    """Ask the copy one question through the adapter and decode the answer."""
    request = request_for(root, as_of=as_of)
    return decode_outcome(adapter.ask(request), sent=request)


def store_of(root: Path) -> FileArtifactStore:
    """A reader over the copy's own declared artifact store."""
    document = load_binding_document(root)
    return FileArtifactStore(
        root=document.artifact_store,
        write_kinds=WriteKinds.declare({document.replay_record_class: (ReplayMint,)}),
    )


def record_at(root: Path, uri: str) -> DecisionReplayRecord:
    """The replay record ``uri`` names, read back from the store."""
    store = store_of(root)
    return DecisionReplayRecord.model_validate_json(
        store.get(content_address=store.resolve_uri(uri=uri))
    )


def demonstration_bindings(record: DecisionReplayRecord, *, tenant: str) -> list[PolicyBinding]:
    """Every dimension-2 binding naming this tenant's demonstration declaration."""
    key = f"{tenant}/{CLASS_ID}"
    return [binding for binding in record.policy_bindings.bindings if binding.key == key]


def tenant_of(root: Path) -> str:
    return str(config_document(root)["tenant_id"])


@pytest.fixture()
def seeded(deployment_root: Path) -> Path:
    """The seeded copy, with the stdio server program beside it for the stdio client."""
    from tests.client.conftest import seed

    seed(deployment_root)
    shutil.copy(STDIO_SERVER, deployment_root.parent / STDIO_SERVER.name)
    return deployment_root


# ---------------------------------------------------------------------------
# The declared instant is the serve instant, and nothing a question carries moves it.
# ---------------------------------------------------------------------------


def test_the_declared_instant_is_the_serve_instant_in_process(seeded: Path) -> None:
    """Served at the declared instant: live, and the record says when."""
    declare(seeded)
    decoded = ask(InProcessAdapter(str(seeded)), seeded, as_of=SEEDED_AT)
    assert decoded.outcome.refusal is None, (
        "the question was refused although the deployment declares a serve"
        f" instant inside the answer's lifetime: {decoded.outcome.refusal}"
    )
    record = record_at(seeded, str(decoded.outcome.replay_ref))
    assert record.content_generation_path.served_at == DECLARED, (
        f"served_at is {record.content_generation_path.served_at}; the deployment"
        f" declares {DECLARED}"
    )


def test_the_question_cannot_move_the_serve_instant(seeded: Path) -> None:
    """A question asked at another instant moves ``asked_at``, never ``served_at``."""
    declare(seeded)
    decoded = ask(InProcessAdapter(str(seeded)), seeded, as_of=OTHER_QUESTION)
    assert decoded.outcome.refusal is None, decoded.outcome.refusal
    record = record_at(seeded, str(decoded.outcome.replay_ref))
    assert record.content_generation_path.served_at == DECLARED
    assert record.content_generation_path.request is not None
    assert record.content_generation_path.request.asked_at == OTHER_QUESTION


def test_as_of_none_resolves_to_the_declared_instant_in_process(seeded: Path) -> None:
    """``as_of=None`` is the deployment's own instant (`D-04`), which is the declared one."""
    declare(seeded)
    decoded = ask(InProcessAdapter(str(seeded)), seeded, as_of=None)
    assert decoded.outcome.refusal is None, decoded.outcome.refusal
    assert decoded.vessel is not None
    assert decoded.vessel.temporal_boundary == DECLARED
    record = record_at(seeded, str(decoded.outcome.replay_ref))
    assert record.content_generation_path.served_at == DECLARED


def test_the_stdio_client_asks_as_of_the_declared_instant(
    seeded: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stdio client resolves ``as_of=None`` to the declared instant, as in-process does.

    ``_call`` is replaced so no child is spawned: what is measured is the
    argument this client puts on the wire, which is the half of the transport
    the client owns (C-15). The server half honors the declaration through the
    same composition the in-process tests above exercise.
    """
    declare(seeded)
    sent: dict[str, Any] = {}

    class _Captured(Exception):
        pass

    async def capture(program: Path, root: Path, arguments: dict[str, object]) -> str:
        sent.update(arguments)
        raise _Captured

    monkeypatch.setattr(McpStdioAdapter, "_call", staticmethod(capture))
    with pytest.raises(_Captured):
        McpStdioAdapter(str(seeded)).ask(request_for(seeded, as_of=None))
    assert sent["asked_at"] == DECLARED.isoformat()


# ---------------------------------------------------------------------------
# One authority: a composed clock beside a declaration is refused by name.
# ---------------------------------------------------------------------------


def test_a_composed_clock_beside_a_declaration_is_refused(seeded: Path) -> None:
    """Two authorities for the serve instant: refused, never a silent winner."""
    from ccf.products.demonstration_clock import DemonstrationServeInstantConflict

    declare(seeded)
    with pytest.raises(DemonstrationServeInstantConflict) as refused:
        ask(InProcessAdapter(str(seeded), clock=lambda: COMPOSED), seeded, as_of=SEEDED_AT)
    assert refused.value.key == f"{tenant_of(seeded)}/{CLASS_ID}"


def test_the_stdio_client_refuses_a_composed_clock_beside_a_declaration(
    seeded: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stdio client holds the same rule, before anything is spawned."""
    from ccf.products.demonstration_clock import DemonstrationServeInstantConflict

    declare(seeded)

    async def never(program: Path, root: Path, arguments: dict[str, object]) -> str:
        raise AssertionError("the stdio client spawned a server before refusing")

    monkeypatch.setattr(McpStdioAdapter, "_call", staticmethod(never))
    with pytest.raises(DemonstrationServeInstantConflict):
        McpStdioAdapter(str(seeded), clock=lambda: COMPOSED).ask(
            request_for(seeded, as_of=None)
        )


def test_a_declaration_registered_after_composition_does_not_reach_the_resolver(
    seeded: Path,
) -> None:
    """T3: a running resolver cannot be switched into demonstration mode."""
    from ccf.controlplane.demonstration_serve_instant import (
        DEMONSTRATION_SERVE_INSTANT,
        DemonstrationServeInstant,
        demonstration_serve_instant_key,
    )

    document = load_binding_document(seeded)
    booted = _boot(document, clock=lambda: COMPOSED)
    try:
        register_typed_at_composition(
            booted.control_plane,
            demonstration_serve_instant_key(tenant_id=booted.fabric.tenant_id),
            DemonstrationServeInstant(serve_instant=DECLARED),
            DEMONSTRATION_SERVE_INSTANT,
        )
        outcome = booted.resolver(
            tenant=booted.fabric.tenant_id,
            product_class=request_for(seeded, as_of=None).product_id,
            version=booted.schema_version,
            perspective=document.perspective,
            request=ProductRequest(
                schema_name=request_for(seeded, as_of=None).product_id,
                schema_version=booted.schema_version,
                subject=document.question.subject,
                intent=document.question.intent,
                freshness=document.question.freshness,
                asked_at=SEEDED_AT,
                parameters=dict(request_for(seeded, as_of=None).parameters),
            ),
        )
        uri = getattr(outcome, "replay_reference", None) or outcome.replay_ref.uri  # type: ignore[union-attr]
        record = record_at(seeded, str(uri))
        assert record.content_generation_path.served_at == COMPOSED
        assert not demonstration_bindings(record, tenant=booted.fabric.tenant_id)
    finally:
        booted.fabric.handle.close()


def _ask_resolver(booted: Any, root: Path) -> Any:
    """Ask a booted deployment's resolver the fixture's question as of :data:`SEEDED_AT`."""
    document = load_binding_document(root)
    wire = request_for(root, as_of=None)
    return booted.resolver(
        tenant=booted.fabric.tenant_id,
        product_class=wire.product_id,
        version=booted.schema_version,
        perspective=document.perspective,
        request=ProductRequest(
            schema_name=wire.product_id,
            schema_version=booted.schema_version,
            subject=document.question.subject,
            intent=document.question.intent,
            freshness=document.question.freshness,
            asked_at=SEEDED_AT,
            parameters=dict(wire.parameters),
        ),
    )


def test_a_declaration_registered_after_composition_takes_effect_only_in_a_resolver_built_after_it(
    seeded: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C1-late, ruled (a) — Dave, 2026-10-08 12:29 MST: *"Running services retain their startup snapshot.
    Document that later registration takes effect only after rebuilding."*

    One Control Plane under two compositions of the in-process adapter's own boot,
    each on the SDK's default clock. The first is built before the declaration is
    registered and keeps serving on that clock, pinning nothing; the second, built
    after, serves at the declared instant and pins the declaration it read.
    """
    from ccf.client.adapters import inprocess
    from ccf.controlplane.demonstration_serve_instant import (
        DEMONSTRATION_SERVE_INSTANT,
        DemonstrationServeInstant,
        demonstration_serve_instant_key,
    )
    from ccf.controlplane.registry import ControlPlaneRegistry

    shared = ControlPlaneRegistry()
    monkeypatch.setattr(inprocess, "ControlPlaneRegistry", lambda: shared)
    document = load_binding_document(seeded)
    before = _boot(document)
    try:
        key = demonstration_serve_instant_key(tenant_id=before.fabric.tenant_id)
        version = register_typed_at_composition(
            shared, key, DemonstrationServeInstant(serve_instant=DECLARED), DEMONSTRATION_SERVE_INSTANT
        )
        retained = _ask_resolver(before, seeded)
        uri = getattr(retained, "replay_reference", None) or retained.replay_ref.uri
        record = record_at(seeded, str(uri))
        assert record.content_generation_path.served_at != DECLARED, "a built resolver read a later declaration"
        assert not demonstration_bindings(record, tenant=before.fabric.tenant_id)
        assert before.declared_clock is None
    finally:
        before.fabric.handle.close()

    after = _boot(document)
    try:
        assert after.declared_clock is not None, "a resolver built after the registration did not read it"
        rebuilt = _ask_resolver(after, seeded)
        uri = getattr(rebuilt, "replay_reference", None) or rebuilt.replay_ref.uri
        record = record_at(seeded, str(uri))
        assert record.content_generation_path.served_at == DECLARED
        assert [(binding.key, binding.version) for binding in demonstration_bindings(
            record, tenant=after.fabric.tenant_id
        )] == [(key, version)]
    finally:
        after.fabric.handle.close()


def test_the_paved_road_refuses_a_declaration_registered_after_open_at_the_next_question(
    tmp_path: Path,
) -> None:
    """C1-late on the paved road: it builds a resolver per question and composes its own clock.

    So a declaration registered into the opened product's Control Plane after
    open is neither retained-around nor honored: the next question is refused by
    name, before anything is acquired, recorded or served.
    """
    from ccf.controlplane.demonstration_serve_instant import (
        DEMONSTRATION_SERVE_INSTANT,
        DemonstrationServeInstant,
        demonstration_serve_instant_key,
    )
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
    from ccf.products.demonstration_clock import DemonstrationServeInstantConflict
    from ccf.products.product import open_product
    from ccf.replay.serve import ServedProduct
    from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust
    from tests.products import paved_fixture as fixture

    # Opened with the fixture's projection, which never withholds: it states `never` (D-IMPL-378 ruling P6 (a)).
    root = fixture.write_tree(
        tmp_path / "deployment",
        config=fixture.producer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER),
        environment=fixture.producer_environment_text(),
    )
    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(control_plane, tenant_id=fixture.PRODUCER_TENANT)
    acquire = fixture.Acquire()
    with open_product(
        erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
        config_root=root,
        scratch=tmp_path / "scratch",
        acquire=acquire,
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"},
        control_plane=control_plane,
        clock=lambda: fixture.ADMITTED_AT,
    ) as opened:
        question = opened.question(
            subject="acct-1",
            asked_at=fixture.ASKED_AT,
            intent="fixture-intent",
            freshness="fixture-freshness",
            parameters={fixture.THRESHOLD_PARAMETER: 1000},
        )
        assert isinstance(opened.answer(question), ServedProduct), "the control question was not served"
        key = demonstration_serve_instant_key(tenant_id=opened.tenant_id)
        register_typed_at_composition(
            control_plane, key, DemonstrationServeInstant(serve_instant=fixture.ADMITTED_AT), DEMONSTRATION_SERVE_INSTANT
        )
        acquired = len(acquire.contexts)
        with pytest.raises(DemonstrationServeInstantConflict) as refused:
            opened.answer(question)
        assert refused.value.key == key
        assert len(acquire.contexts) == acquired, "the refused question acquired"


# ---------------------------------------------------------------------------
# Audit by construction: every record under the declaration pins it.
# ---------------------------------------------------------------------------


def test_a_served_record_pins_the_declaration(seeded: Path) -> None:
    """Dimension 2 names the exact declaration that set ``served_at``."""
    from ccf.controlplane.demonstration_serve_instant import DemonstrationServeInstant

    declare(seeded)
    decoded = ask(InProcessAdapter(str(seeded)), seeded, as_of=SEEDED_AT)
    assert decoded.outcome.refusal is None, decoded.outcome.refusal
    record = record_at(seeded, str(decoded.outcome.replay_ref))
    pins = demonstration_bindings(record, tenant=tenant_of(seeded))
    assert pins == [
        PolicyBinding(
            key=f"{tenant_of(seeded)}/{CLASS_ID}",
            version=content_hash(DemonstrationServeInstant(serve_instant=DECLARED)),
        )
    ], record.policy_bindings.bindings


def test_a_refusal_record_pins_the_declaration(seeded: Path) -> None:
    """A governed refusal under the declaration is a demonstration record too."""
    from ccf.controlplane.demonstration_serve_instant import DemonstrationServeInstant

    declare(seeded)
    request = request_for(seeded, as_of=SEEDED_AT)
    unanswerable = WireRequest(
        product_id=request.product_id, parameters={}, temporal_boundary=SEEDED_AT
    )
    decoded = decode_outcome(InProcessAdapter(str(seeded)).ask(unanswerable), sent=unanswerable)
    assert decoded.outcome.refusal is not None, "a question missing its required argument was served"
    record = record_at(seeded, str(decoded.outcome.replay_ref))
    assert record.content_generation_path.served_at == DECLARED
    pins = demonstration_bindings(record, tenant=tenant_of(seeded))
    assert pins == [
        PolicyBinding(
            key=f"{tenant_of(seeded)}/{CLASS_ID}",
            version=content_hash(DemonstrationServeInstant(serve_instant=DECLARED)),
        )
    ], record.policy_bindings.bindings


# ---------------------------------------------------------------------------
# Never usable in production (option (b), ruled): development substrates only.
# ---------------------------------------------------------------------------


def test_a_declaration_over_a_non_development_graph_substrate_is_refused(
    seeded: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fabric whose graph adapter is not the SDK's SQLite or in-memory reference refuses."""
    from ccf.client.adapters import inprocess
    from ccf.products.demonstration_clock import DemonstrationServeInstantRefused

    declare(seeded)
    booting = inprocess.load_config_and_boot

    def on_a_network_substrate(*args: Any, **kwargs: Any) -> Any:
        fabric = booting(*args, **kwargs)
        fabric.handle.adapter = AdapterPin(
            name="postgres", version=fabric.handle.adapter.version, secret_refs=()
        )
        return fabric

    monkeypatch.setattr(inprocess, "load_config_and_boot", on_a_network_substrate)
    with pytest.raises(DemonstrationServeInstantRefused) as refused:
        ask(InProcessAdapter(str(seeded)), seeded, as_of=SEEDED_AT)
    assert refused.value.reason == "graph-substrate-not-development"


def test_a_declaration_over_a_non_file_artifact_store_is_refused(
    seeded: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A store that is not the SDK's file-backed development store refuses."""
    from ccf.client.adapters import inprocess
    from ccf.products.demonstration_clock import DemonstrationServeInstantRefused

    declare(seeded)

    class _AnotherStore:
        """Any store that is not the SDK's file-backed one, delegating to a real one."""

        def __init__(self, **kwargs: Any) -> None:
            self._inner = FileArtifactStore(**kwargs)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

    monkeypatch.setattr(inprocess, "FileArtifactStore", _AnotherStore)
    with pytest.raises(DemonstrationServeInstantRefused) as refused:
        ask(InProcessAdapter(str(seeded)), seeded, as_of=SEEDED_AT)
    assert refused.value.reason == "artifact-store-not-development"


# ---------------------------------------------------------------------------
# Confinement: only the serve clock moves.
# ---------------------------------------------------------------------------


def test_the_erasure_consult_keeps_the_composition_clock(seeded: Path) -> None:
    """The erasure audit stamp is never the declared instant (T5)."""
    from ccf.products.demonstration_clock import DeclaredServeClock

    declare(seeded)
    booted = _boot(load_binding_document(seeded))
    try:
        serve_clock = booted.resolver.admission_clock  # type: ignore[attr-defined]
        assert isinstance(serve_clock, DeclaredServeClock)
        assert serve_clock() == DECLARED
        erasure_clock = booted.resolver.artifact_store._clock  # type: ignore[attr-defined]
        assert not isinstance(erasure_clock, DeclaredServeClock)
        assert erasure_clock() != DECLARED
    finally:
        booted.fabric.handle.close()


def test_only_the_sdks_sqlite_and_in_memory_adapters_are_development_references() -> None:
    """Exactly two built-in adapters declare ``development_reference``.

    The guard asks the booted adapter's own registration, so this holds the
    declarations: the SQLite and in-memory reference adapters say yes, and every
    networked adapter the SDK ships says no. An adapter that newly claims the
    flag — or a development reference that loses it — is red here.
    """
    from ccf.graph.registry import _builtin_names, resolve

    built_in = set(_builtin_names())
    assert {"sqlite", "memory"} < built_in, built_in
    declaring = {name for name in built_in if resolve(name).registration.development_reference}
    assert declaring == {"sqlite", "memory"}, declaring


def test_the_records_pin_resolves_at_its_recorded_version(seeded: Path) -> None:
    """The pin names the exact declaration that set ``served_at``, resolvable as replay resolves it.

    Replay checks every dimension-2 binding with the Control Plane's exact-version
    read, ``control_plane.resolve(key, version)``
    (`ccf.replay.engine._resolve_bindings`), and nothing special-cases this one.
    So the claim is measured at that call: against the deployment's own Control
    Plane the record's pin resolves to the declaration whose instant the record
    carries as ``served_at``; against a Control Plane booted from the same config
    WITHOUT the declaration it does not resolve, so a demonstration record cannot
    be replayed as an ordinary one.

    The full reconstruction — every binding resolved at its pinned version,
    then the record's own claims held — is measured end to end by
    :func:`test_a_demonstration_refusal_record_replays_end_to_end` below.
    """
    from ccf.client.adapters import inprocess
    from ccf.controlplane.demonstration_serve_instant import DemonstrationServeInstant
    from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneRegistry
    from ccf.deployment.config import load_config_and_boot

    undeclared_config = seeded.parent / "undeclared_ccf_config.yaml"
    shutil.copy(seeded / "ccf_config.yaml", undeclared_config)
    declare(seeded)
    decoded = ask(InProcessAdapter(str(seeded)), seeded, as_of=SEEDED_AT)
    assert decoded.outcome.refusal is None, decoded.outcome.refusal
    record = record_at(seeded, str(decoded.outcome.replay_ref))
    (pin,) = demonstration_bindings(record, tenant=tenant_of(seeded))

    booted = inprocess._BOOT_CACHE[seeded.resolve()]
    declared = booted.control_plane.resolve(pin.key, pin.version)
    assert isinstance(declared, DemonstrationServeInstant)
    assert declared.serve_instant == record.content_generation_path.served_at == DECLARED

    without = ControlPlaneRegistry()
    other = load_config_and_boot(
        undeclared_config,
        registry=without,
        connection=load_binding_document(seeded).connection,
        read_only=True,
    )
    try:
        with pytest.raises(ControlPlaneMissing):
            without.resolve(pin.key, pin.version)
    finally:
        other.handle.close()


def test_a_demonstration_refusal_record_replays_end_to_end(seeded: Path) -> None:
    """A refusal written under the declaration reconstructs — and needs the declaration to.

    `ccf.replay.engine.replay_refusal` runs `replay`'s prologue (the record at its
    exact address, every dimension-2 binding at its pinned version) and, for a
    refusal decided before projection, consults no environment. Against the
    deployment's own Control Plane the record reconstructs. Against that SAME
    Control Plane with only the declaration's key hidden it is refused, on that
    key — so the pin is resolved, not skipped, and nothing else differs between
    the two runs.

    Possible since the request contract is registered before the resolution that
    pins it (lane ``378d-replayfix``, CP17-F-09): before that, this fixture's
    refusal records stopped at the request contract's pin with no declaration in
    force at all. A Control Plane booted afresh, which has answered nothing,
    still stops there today (ruling R-A (b) addresses it), which is why the
    control hides one key rather than booting a second registry.
    """
    from ccf.client.adapters import inprocess
    from ccf.controlplane.registry import ControlPlaneMissing
    from ccf.replay.engine import RefusalReplayOutcome, ReplayUnresolvable, replay_refusal

    declare(seeded)
    request = request_for(seeded, as_of=SEEDED_AT)
    unanswerable = WireRequest(
        product_id=request.product_id, parameters={}, temporal_boundary=SEEDED_AT
    )
    decoded = decode_outcome(InProcessAdapter(str(seeded)).ask(unanswerable), sent=unanswerable)
    assert decoded.outcome.refusal is not None
    record = record_at(seeded, str(decoded.outcome.replay_ref))
    (pin,) = demonstration_bindings(record, tenant=tenant_of(seeded))
    store = store_of(seeded)
    address = store.resolve_uri(uri=str(decoded.outcome.replay_ref))
    booted = inprocess._BOOT_CACHE[seeded.resolve()]

    reconstructed = replay_refusal(
        record_address=address,
        store=store,
        reader=booted.fabric.handle.reader,
        control_plane=booted.control_plane,
        environment=None,  # type: ignore[arg-type]  # not consulted before projection
    )
    assert isinstance(reconstructed, RefusalReplayOutcome)
    assert reconstructed.record_content_address == address

    class _WithoutTheDeclaration:
        """The deployment's own Control Plane with exactly one key hidden."""

        def __init__(self, inner: Any, hidden: str) -> None:
            self._inner = inner
            self._hidden = hidden

        def resolve(self, key: str, version: str) -> object:
            if key == self._hidden:
                raise ControlPlaneMissing(f"hidden by the control: {key!r}")
            return self._inner.resolve(key, version)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

    with pytest.raises(ReplayUnresolvable) as refused:
        replay_refusal(
            record_address=address,
            store=store,
            reader=booted.fabric.handle.reader,
            control_plane=_WithoutTheDeclaration(booted.control_plane, pin.key),  # type: ignore[arg-type]
            environment=None,  # type: ignore[arg-type]
        )
    assert f"{tenant_of(seeded)}/{CLASS_ID}" in str(refused.value), str(refused.value)
