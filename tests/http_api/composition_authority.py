"""The composition recipe, for tests that stand in for a deployment (D-IMPL-354).

A test fixture that registers a Control Plane artifact, builds a refusal
recorder, or files a governed record IS the composition root of the deployment
it stands in for. Under ``D-IMPL-353`` §1.2 every such write requires a
capability, and under ``D-IMPL-354`` the ONLY sanctioned way a composition
root obtains one is the recipe, verbatim::

    event = registry.audit_log.append(
        action="composition", key=<resource>, version=<Kind.action_id>,
        resolved=True, occurred_at=<the composition's clock reading>,
        actor=COMPOSITION_PRINCIPAL,
    )
    capability = mint_at_composition(
        <Kind>, tenant=<tenant>, principal=COMPOSITION_PRINCIPAL,
        resource=<resource>, decision_id=content_hash(event),
    )

``Kind`` is :class:`~ccf.authz.capability.Register` (resource = ONE exact
Control Plane key) or :class:`~ccf.authz.capability.ReplayMint` (resource =
ONE evidence artifact class id) and nothing else; the overloads and the runtime
check on ``mint_at_composition`` refuse every door kind. This module spells
the recipe once so that no fixture spells it differently, no fixture fabricates
an ``Authorized``, and no fixture names the sentinel.

Written by Lane J-RUNTIME beside ``gate_fixtures.py``; J-SRC builds a shared
``tests/composition.py`` in parallel and the join dedupes the two. Everything
here imports only ``ccf.*``, so the module loads under either spelling a test
tree uses (``http_api.composition_authority`` from a bare child process with
``tests/`` on its path, ``tests.http_api.composition_authority`` from pytest).

Tenant names, keys and class ids are the caller's — a test IS the deployment
(CINV-01 applied to test data).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactStoreProtocol, WriteKinds
from ccf.authz.capability import (
    COMPOSITION_PRINCIPAL,
    ActionKind,
    Authorized,
    Execute,
    Register,
    ReplayMint,
    Resume,
    mint_at_composition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import ArtifactClass
from ccf.controlplane.registry import ControlPlaneRegistry, RegistrationRefusal
from ccf.products.resolver import ReplayRefusalRecorder

__all__ = [
    "composition_register",
    "composition_replay_mint",
    "deployment_store",
    "deployment_write_kinds",
    "refusal_recorder",
    "register_at_composition",
    "register_typed_at_composition",
    "register_versioned_at_composition",
    "trace_write_kinds",
]

#: The workflow engine's trace class, spelled here rather than imported from
#: ``ccf_runtime`` so a bare child process that never imports the engine can
#: still declare it. ``tests/workflow/test_engine.py`` pins the two equal.
WORKFLOW_TRACE_CLASS = "ccf.workflow-trace"

Clock = Callable[[], datetime]


def _now() -> datetime:
    return datetime.now(UTC)


def _tenant_of(key: str, tenant: str | None) -> str:
    """The key's tenant segment unless the caller states one.

    The Control Plane key grammar is ``{tenant}/{class}/{name}`` and the
    registry compares the segment to the capability's tenant once, at
    ``register`` (§1.3). A composition root registering ``acme/policy/x``
    is acting for ``acme``; a fixture that wants the disagreeing case states
    another tenant explicitly and gets the registry's refusal.
    """
    if tenant is not None:
        return tenant
    segment, separator, _ = key.partition("/")
    if not separator or not segment:
        raise ValueError(
            f"key {key!r} carries no tenant segment; a composition root"
            " registers under `{tenant}/{class}/{name}` or states the tenant"
            " it acts for (D-IMPL-353 §1.3)"
        )
    return segment


def composition_register(
    registry: ControlPlaneRegistry,
    key: str,
    *,
    tenant: str | None = None,
    clock: Clock | None = None,
) -> Authorized[Register]:
    """The recipe for ``Register`` on exactly ``key`` — the decision recorded, then the mint."""
    acting_for = _tenant_of(key, tenant)
    event = registry.audit_log.append(
        action="composition",
        key=key,
        version=Register.action_id,
        resolved=True,
        occurred_at=(clock or _now)(),
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        Register,
        tenant=acting_for,
        principal=COMPOSITION_PRINCIPAL,
        resource=key,
        decision_id=content_hash(event),
    )


def composition_replay_mint(
    registry: ControlPlaneRegistry,
    *,
    tenant: str,
    artifact_class: str,
    clock: Clock | None = None,
) -> Authorized[ReplayMint]:
    """The recipe for ``ReplayMint`` on exactly ``artifact_class`` for ``tenant``."""
    event = registry.audit_log.append(
        action="composition",
        key=artifact_class,
        version=ReplayMint.action_id,
        resolved=True,
        occurred_at=(clock or _now)(),
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        ReplayMint,
        tenant=tenant,
        principal=COMPOSITION_PRINCIPAL,
        resource=artifact_class,
        decision_id=content_hash(event),
    )


def register_at_composition(
    registry: ControlPlaneRegistry,
    key: str,
    artifact: object,
    *,
    tenant: str | None = None,
    clock: Clock | None = None,
) -> str:
    """``registry.register`` under a composition-minted ``Register`` for ``key``."""
    return registry.register(
        composition_register(registry, key, tenant=tenant, clock=clock), artifact
    )


def register_typed_at_composition(
    registry: ControlPlaneRegistry,
    key: str,
    artifact: object,
    artifact_class: ArtifactClass,
    *,
    tenant: str | None = None,
    clock: Clock | None = None,
) -> str:
    """``registry.register_typed`` under a composition-minted ``Register`` for ``key``."""
    return registry.register_typed(
        composition_register(registry, key, tenant=tenant, clock=clock),
        artifact,
        artifact_class,
    )


def register_versioned_at_composition(
    registry: ControlPlaneRegistry,
    key: str,
    artifact: object,
    artifact_class: ArtifactClass,
    *,
    reissuable: bool = False,
    tenant: str | None = None,
    clock: Clock | None = None,
) -> str | RegistrationRefusal:
    """``registry.register_versioned`` under a composition-minted ``Register`` for ``key``."""
    return registry.register_versioned(
        composition_register(registry, key, tenant=tenant, clock=clock),
        artifact,
        artifact_class,
        reissuable=reissuable,
    )


def trace_write_kinds() -> WriteKinds:
    """The declaration a deployment that runs workflows makes: the trace class under ``Execute | Resume``."""
    return WriteKinds.declare({WORKFLOW_TRACE_CLASS: (Execute, Resume)})


def deployment_write_kinds(
    *replay_classes: str, workflow_traces: bool = False
) -> WriteKinds:
    """What a test deployment's mechanism writes: each named class under ``ReplayMint``, and the trace class if it runs workflows."""
    declared: dict[str, tuple[type[ActionKind], ...]] = {
        artifact_class: (ReplayMint,) for artifact_class in replay_classes
    }
    if workflow_traces:
        declared[WORKFLOW_TRACE_CLASS] = (Execute, Resume)
    return WriteKinds(declared)


def deployment_store(
    root: Path | str, *replay_classes: str, workflow_traces: bool = False
) -> FileArtifactStore:
    """A file store declaring exactly what this test deployment's mechanism writes."""
    return FileArtifactStore(
        root=root,
        write_kinds=deployment_write_kinds(*replay_classes, workflow_traces=workflow_traces),
    )


def refusal_recorder(
    registry: ControlPlaneRegistry,
    *,
    store: ArtifactStoreProtocol,
    tenant: str,
    replay_record_class: str,
    assembly_mode: Any = "algorithmic",
    policy_bundle_pin: Any = None,
    disclosure_level_for: Any = None,
    clock: Clock | None = None,
) -> ReplayRefusalRecorder:
    """The SDK's recorder, handed a composition-minted ``ReplayMint`` for its class.

    ``registry`` is where the composition decision is recorded; ``store`` must
    declare ``replay_record_class`` under ``ReplayMint`` or the recorder's first
    governed determination fails closed at the store (and ``create_app``
    refuses to build over it). One helper so every test's recorder is built the
    one way, and so the join has one line to change if the recorder's shape
    moves under J-SRC.
    """
    authorized = composition_replay_mint(
        registry, tenant=tenant, artifact_class=replay_record_class, clock=clock
    )
    extra: dict[str, Any] = {}
    if disclosure_level_for is not None:
        extra["disclosure_level_for"] = disclosure_level_for
    return ReplayRefusalRecorder(
        authorized=authorized,
        artifact_store=store,
        assembly_mode=assembly_mode,
        policy_bundle_pin=policy_bundle_pin,
        **extra,
    )
