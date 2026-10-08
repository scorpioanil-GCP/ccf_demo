"""Record provenance at the replay engine's read: bytes the record writer did not file are not a record (D-IMPL-378, item 3).

**The hole, as worded.** Lane 378-clientlane measured, and the coordinator
reproduced on the integration tree, that SDK code reading a store DIRECTLY
accepts a record-shaped artifact that a tenant's own principal filed on its
client lane — an ordinary ``ArtifactWrite`` for class ``"c"``, the lane HTTP
``POST /artifact`` files on — as a Decision Replay record naming another
principal: :func:`~ccf.replay.engine.resolve_artifact` and
:func:`~ccf.replay.engine.resolve_artifact_at_uri` returned it as a
``DecisionReplayRecord``, over the raw file store AND the erasure-consulting
composition, and :func:`~ccf.replay.engine.replay_refusal` verified it.

**Dave's ruling (item 3), verbatim:** *"Same-tenant record-shaped bytes: They
may remain ordinary client artifacts only if their untrusted origin is explicit
and consumers cannot accept them as governed evidence. Otherwise refuse that
path until provenance is enforced."*

**The rule held here** is the one
``ccf_runtime.authz.delivery_boundary.govern_dereference`` already enforces
("Provenance, before any hold"): the store's own naming must show the address
filed by the fabric's record writer — under a class the store's
:class:`~ccf.artifacts.protocol.WriteKinds` declares under ``ReplayMint``, a
kind no door can mint — under the tenant the record names. Anything else is
not a record: the engine answers exactly as it answers for a missing record,
:class:`~ccf.replay.engine.ReplayUnresolvable`, and the cause it chains names
the mechanism. A store that cannot answer the question refuses by name.

Every genuine record here is written by the fabric's own writer through the
shipped resolver (``tests/products/composite_fixture.py``), and every control
is positive: the genuine record still resolves or replays.

Tenant, principal, class and name strings are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator
from datetime import UTC, datetime
from types import ModuleType
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import compose_erasure_consult
from ccf.replay.engine import (
    RefusalReplayOutcome,
    ReplayOutcome,
    ReplayUnresolvable,
    replay,
    replay_refusal,
    resolve_artifact,
    resolve_artifact_at_uri,
)
from ccf.replay.record import DecisionReplayRecord
from tests.composition import declared_erasure_trust, no_erasures
from tests.controlplane.capabilities import capability
from tests.products.composite_fixture import _Booted, _child_door, ask_composite, boot_composite
from tests.products.test_d_impl_339_child_contract_view import (
    _ChildReadingFactory,
    _FreshEnvironment,
    _one_shot,
    _refused,
    _served,
    _wired,
)
from tests.products.test_d_impl_344_refusal_reconstruction import _NeverConsulted, _fresh_environment
from tests.products.test_resolver_seam import REPLAY_RECORD_CLASS
from tests.replay.authority import mechanism_put

#: The client lane: a class the deployment never declared mechanism-written.
CLIENT_CLASS = "c"
#: The principal a forgery names — not the principal the decision was made for.
VICTIM = "victim-principal"
#: Another tenant of the same deployment, holding its OWN record writer.
OTHER_TENANT = "tenant-other"
CONSULT_INSTANT = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def _provenance() -> ModuleType:
    """The provenance module — imported only after a refusal is observed, so
    that before the fix this file fails on the behavior, never on an import."""
    import ccf.replay.provenance as provenance  # noqa: PLC0415

    return provenance


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    yield from boot_composite(tmp_path)


def _fresh(booted: _Booted) -> FileArtifactStore:
    """The deployment's store, reopened — nothing the serving path held in memory."""
    return FileArtifactStore(root=booted.store.root, write_kinds=booted.store.write_kinds)


def _composed(store: Any) -> Any:
    """The store as a deployment composes it: the erasure consult around it."""
    return compose_erasure_consult(
        store,
        index=no_erasures(),
        audit_log=ControlPlaneRegistry().audit_log,
        clock=lambda: CONSULT_INSTANT,
        control_plane=ControlPlaneRegistry(),
        erasure_trust=declared_erasure_trust(),
    )


def _naming_victim(record: DecisionReplayRecord) -> DecisionReplayRecord:
    """The genuine record, re-pointed at :data:`VICTIM` — still a valid record shape."""
    return record.model_copy(
        update={
            "perspective_conditioning": record.perspective_conditioning.model_copy(
                update={"principal_id": VICTIM}
            )
        }
    )


def _forge_on_client_lane(store: Any, forged: DecisionReplayRecord, *, name: str = "innocuous") -> ArtifactRef:
    """The record's OWN tenant files ``forged`` on its client lane — an ordinary ``ArtifactWrite``."""
    return store.put(
        capability(ArtifactWrite, tenant=forged.tenant_id, resource=f"{CLIENT_CLASS}/{name}"),
        json.loads(canonical_bytes(forged)),
    )


def _a_refused_decision(booted: _Booted) -> tuple[str, DecisionReplayRecord]:
    """A refused composite decision the fabric's record writer filed: (address, record)."""
    outcome = ask_composite(_wired(booted, grant=False, plan_factory=_ChildReadingFactory()))
    record = _refused(booted, outcome, "composite-child-refusal")
    return _fresh(booted).resolve_uri(uri=outcome.replay_reference), record


def _assert_refused_for_provenance(refused: pytest.ExceptionInfo[ReplayUnresolvable]) -> None:
    cause = refused.value.__cause__
    assert isinstance(cause, _provenance().RecordNotFiledByRecordWriter), (
        f"the refusal is not the provenance mechanism's: cause={cause!r}"
    )


# --- resolve_artifact / resolve_artifact_at_uri ------------------------------------


@pytest.mark.parametrize("composition", ["raw", "composed"])
def test_resolve_artifact_refuses_a_record_forged_on_the_tenants_own_client_lane(
    booted: _Booted, composition: str
) -> None:
    address, record = _a_refused_decision(booted)
    store = _fresh(booted) if composition == "raw" else _composed(_fresh(booted))
    # Control: the record the fabric's writer filed resolves.
    assert resolve_artifact(store=store, content_address=address, contract=DecisionReplayRecord) == record

    forged = _naming_victim(record)
    filed = _forge_on_client_lane(store, forged)
    assert filed.content_address == content_hash(forged) != address

    with pytest.raises(ReplayUnresolvable) as refused:
        resolve_artifact(store=store, content_address=filed.content_address, contract=DecisionReplayRecord)
    _assert_refused_for_provenance(refused)


@pytest.mark.parametrize("composition", ["raw", "composed"])
def test_resolve_artifact_at_uri_refuses_a_record_forged_on_the_tenants_own_client_lane(
    booted: _Booted, composition: str
) -> None:
    address, record = _a_refused_decision(booted)
    store = _fresh(booted) if composition == "raw" else _composed(_fresh(booted))
    (genuine_name,) = [named for named in _fresh(booted).names_at(content_address=address)]
    genuine_uri = (
        f"ccf-artifact://{genuine_name.tenant_id}/{genuine_name.artifact_class}/{genuine_name.name}@{address}"
    )
    assert resolve_artifact_at_uri(store=store, uri=genuine_uri, contract=DecisionReplayRecord) == record

    filed = _forge_on_client_lane(store, _naming_victim(record))
    with pytest.raises(ReplayUnresolvable) as refused:
        resolve_artifact_at_uri(store=store, uri=filed.uri, contract=DecisionReplayRecord)
    _assert_refused_for_provenance(refused)


def test_a_record_filed_by_ANOTHER_tenants_record_writer_is_not_this_tenants_record(
    booted: _Booted,
) -> None:
    """The tenant clause: a ``ReplayMint`` class is not enough — the filing must
    be under the tenant the record names, as ``govern_dereference`` requires."""
    address, record = _a_refused_decision(booted)
    store = _fresh(booted)
    forged = _naming_victim(record)
    filed = mechanism_put(
        store, tenant=OTHER_TENANT, artifact_class=REPLAY_RECORD_CLASS, name="foreign", artifact=forged
    )
    assert [(n.tenant_id, n.artifact_class) for n in store.names_at(content_address=filed.content_address)] == [
        (OTHER_TENANT, REPLAY_RECORD_CLASS)
    ]
    assert forged.tenant_id != OTHER_TENANT

    with pytest.raises(ReplayUnresolvable) as refused:
        resolve_artifact(store=store, content_address=filed.content_address, contract=DecisionReplayRecord)
    _assert_refused_for_provenance(refused)
    # Control: the same tenant's genuine record still resolves.
    assert resolve_artifact(store=store, content_address=address, contract=DecisionReplayRecord) == record


def test_the_same_bytes_filed_by_the_record_writer_resolve_whatever_else_names_them(
    booted: _Booted,
) -> None:
    """Content addressing: identical bytes are one artifact. A client-lane copy of
    a GENUINE record is the genuine record, and its client-lane URI resolves —
    the rule refuses bytes the writer never filed, never a second name."""
    address, record = _a_refused_decision(booted)
    store = _fresh(booted)
    copy = _forge_on_client_lane(store, record, name="copy")
    assert copy.content_address == address
    assert resolve_artifact_at_uri(store=store, uri=copy.uri, contract=DecisionReplayRecord) == record


# --- replay / replay_refusal -----------------------------------------------------


def test_replay_refusal_refuses_a_refused_record_forged_on_the_tenants_own_client_lane(
    booted: _Booted,
) -> None:
    address, record = _a_refused_decision(booted)
    store = _fresh(booted)
    # Control: the genuine refused decision reconstructs.
    genuine = replay_refusal(
        record_address=address,
        store=store,
        reader=booted.fabric.handle.reader,
        control_plane=booted.control_plane,
        environment=_NeverConsulted(),
    )
    assert isinstance(genuine, RefusalReplayOutcome) and genuine.record == record

    filed = _forge_on_client_lane(store, _naming_victim(record))
    with pytest.raises(ReplayUnresolvable) as refused:
        replay_refusal(
            record_address=filed.content_address,
            store=store,
            reader=booted.fabric.handle.reader,
            control_plane=booted.control_plane,
            environment=_NeverConsulted(),
        )
    _assert_refused_for_provenance(refused)


def _replay_environment(booted: _Booted, record: DecisionReplayRecord) -> _FreshEnvironment:
    built = _fresh_environment(booted, record)
    path = record.content_generation_path
    return _FreshEnvironment(
        request=path.request,
        required=tuple(path.operator_plan),
        operators=built._operators,
        ttl_seconds=built._ttl,
    )


def test_replay_refuses_a_served_record_forged_on_the_tenants_own_client_lane(
    booted: _Booted,
) -> None:
    door = _one_shot(_child_door(booted))
    served = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    product, record = _served(booted, served)
    store = _fresh(booted)
    # Control: the genuine served decision reproduces its product.
    genuine = replay(
        record_address=served.replay_ref.content_address,
        store=store,
        reader=booted.fabric.handle.reader,
        control_plane=booted.control_plane,
        environment=_replay_environment(booted, record),
    )
    assert isinstance(genuine, ReplayOutcome)
    assert genuine.product_content_address == content_hash(product)

    filed = _forge_on_client_lane(store, _naming_victim(record))
    with pytest.raises(ReplayUnresolvable) as refused:
        replay(
            record_address=filed.content_address,
            store=store,
            reader=booted.fabric.handle.reader,
            control_plane=booted.control_plane,
            environment=_replay_environment(booted, record),
        )
    _assert_refused_for_provenance(refused)


# --- a store that cannot attribute a filing ----------------------------------------


class _WithoutNaming:
    """A third-party substrate that keeps the four Protocol verbs and drops one of
    the two readings attribution needs — ``names_at`` or ``write_kinds``."""

    def __init__(self, inner: FileArtifactStore, *, drop: str) -> None:
        self._inner = inner
        self._drop = drop

    def __getattr__(self, attribute: str) -> Any:
        if attribute == self._drop:
            raise AttributeError(attribute)
        return getattr(self._inner, attribute)


@pytest.mark.parametrize("composition", ["raw", "composed"])
@pytest.mark.parametrize("drop", ["names_at", "write_kinds"])
def test_a_store_that_cannot_attribute_a_filing_refuses_a_genuine_record_by_name(
    booted: _Booted, drop: str, composition: str
) -> None:
    """Fail closed: a store that cannot say who filed an address cannot hand the
    engine a record, even a genuine one — refused by name, never served."""
    address, _record = _a_refused_decision(booted)
    unattributing = _WithoutNaming(_fresh(booted), drop=drop)
    store = unattributing if composition == "raw" else _composed(unattributing)

    with pytest.raises(TypeError) as refused:
        resolve_artifact(store=store, content_address=address, contract=DecisionReplayRecord)
    assert isinstance(refused.value, _provenance().UnattributableRecordStore), refused.value
