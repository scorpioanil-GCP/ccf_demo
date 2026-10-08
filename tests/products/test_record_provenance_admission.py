"""Record provenance where products read a record from their store: child admission and ``record_of`` (D-IMPL-378, item 3).

**The hole, as worded.** The SDK code that turns stored bytes into a
``DecisionReplayRecord`` outside the replay engine accepted a record-shaped
artifact that a tenant's own principal filed on its client lane (an ordinary
``ArtifactWrite`` for class ``"c"``):

* child admission — ``GrantBoundChildResolver._touched_entities`` — took the
  forged record's touched entities as the locally dispatched child's own
  execution record, so the eligibility check asked the register about reads
  the child never made (lane 378-clientlane's in-process probe);
* :meth:`~ccf.products.product.OpenedProduct.record_of` returned the forgery
  as "the decision record behind" an outcome naming its address or URI.

**Dave's ruling (item 3), verbatim:** *"Same-tenant record-shaped bytes: They
may remain ordinary client artifacts only if their untrusted origin is explicit
and consumers cannot accept them as governed evidence. Otherwise refuse that
path until provenance is enforced."*

The rule is ``govern_dereference``'s "Provenance, before any hold": a record is
read only where the store's own naming shows the fabric's record writer filed
the address — under a ``ReplayMint`` class of the store's ``WriteKinds`` —
under the tenant the record names. Bytes filed any other way are answered as
a missing record is (:class:`~ccf.artifacts.protocol.ArtifactNotFound`), and
the type raised names the mechanism. Every control is positive: the honest
pairing still serves, and the genuine record still reads.

Tenant, principal, class and entity strings are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator, Mapping
from types import ModuleType
from typing import Any

import pytest

from ccf.artifacts.protocol import ArtifactNotFound
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import DoorOutcome
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.controlplane.capabilities import capability
from tests.products import test_paved_road as pr
from tests.products.composite_fixture import _Booted, _child_door, ask_composite, boot_composite
from tests.products.test_d_impl_339_child_contract_view import _ChildReadingFactory, _wired

#: The client lane: a class the deployment never declared mechanism-written.
CLIENT_CLASS = "c"
#: The principal a forged decision record names.
VICTIM = "victim-principal"
#: An entity the child never read, planted in the forged record's dimension 1.
FORGED_ENTITY = "forged:entity"


def _provenance() -> ModuleType:
    """The provenance module — imported only after a refusal is observed, so
    that before the fix this file fails on the behavior, never on an import."""
    import ccf.replay.provenance as provenance  # noqa: PLC0415

    return provenance


def _file_on_client_lane(store: Any, forged: DecisionReplayRecord, *, name: str) -> Any:
    """The record's OWN tenant files ``forged`` on its client lane — an ordinary ``ArtifactWrite``."""
    return store.put(
        capability(ArtifactWrite, tenant=forged.tenant_id, resource=f"{CLIENT_CLASS}/{name}"),
        json.loads(canonical_bytes(forged)),
    )


# --- child admission ----------------------------------------------------------------


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    yield from boot_composite(tmp_path)


class _ForgingChildDoor:
    """The child's REAL door. With :attr:`forge` set it keeps the honest product
    and the honest address and swaps only the record reference, for a copy of
    the child's own record — same product address, forged touched entities —
    that the tenant filed on its own client lane."""

    def __init__(self, booted: _Booted) -> None:
        self._inner = _child_door(booted)
        self._store = booted.store
        self.forge = False
        self.forged_uri: str | None = None

    def __call__(self, arguments: Mapping[str, str]) -> Mapping[str, str]:
        answered = self._inner(arguments)
        if not self.forge:
            return answered
        outcome = DoorOutcome.model_validate_json(answered["outcome"])
        assert outcome.replay_ref is not None
        genuine = DecisionReplayRecord.model_validate_json(
            self._store.get(content_address=self._store.resolve_uri(uri=outcome.replay_ref))
        )
        forged = genuine.model_copy(
            update={
                "context_fabric_snapshot": genuine.context_fabric_snapshot.model_copy(
                    update={"touched_entities": (FORGED_ENTITY,)}
                )
            }
        )
        assert forged.content_generation_path.product_content_address == (
            genuine.content_generation_path.product_content_address
        )
        filed = _file_on_client_lane(self._store, forged, name="child-record")
        self.forged_uri = filed.uri
        return {"outcome": outcome.model_copy(update={"replay_ref": filed.uri}).model_dump_json()}


def test_child_admission_refuses_a_child_record_forged_on_the_tenants_own_client_lane(
    booted: _Booted,
) -> None:
    door = _ForgingChildDoor(booted)
    resolver = _wired(booted, door=door, plan_factory=_ChildReadingFactory())
    # Control: the honest pairing — the child's own record — serves.
    assert isinstance(ask_composite(resolver), ServedProduct)

    door.forge = True
    with pytest.raises(ArtifactNotFound) as refused:
        ask_composite(resolver)
    assert door.forged_uri is not None, "the forging door was never asked"
    assert isinstance(refused.value, _provenance().RecordNotFiledByRecordWriter), refused.value


# --- OpenedProduct.record_of ------------------------------------------------------------


def _naming_victim(record: DecisionReplayRecord) -> DecisionReplayRecord:
    return record.model_copy(
        update={
            "perspective_conditioning": record.perspective_conditioning.model_copy(
                update={"principal_id": VICTIM}
            )
        }
    )


def test_record_of_refuses_a_record_forged_on_the_tenants_own_client_lane(tmp_path: pathlib.Path) -> None:
    root, scratch = pr._write_tree(tmp_path), tmp_path / "scratch"
    with pr._open(root, scratch) as opened:
        served = opened.answer(pr._question(opened))
        assert isinstance(served, ServedProduct), served
        genuine = opened.record_of(served)  # control: the served decision's own record
        refusal = opened.answer(pr._question(opened, no_such_parameter=1))
        assert isinstance(refusal, RefusalEnvelope), refusal
        assert opened.record_of(refusal).content_generation_path.request is not None  # control

        filed = _file_on_client_lane(opened.artifact_store, _naming_victim(genuine), name="innocuous")

        # A served outcome naming the forgery's address...
        with pytest.raises(ArtifactNotFound) as by_address:
            opened.record_of(ServedProduct(product=served.product, replay_ref=filed))
        assert isinstance(by_address.value, _provenance().RecordNotFiledByRecordWriter), by_address.value
        # ...and a refusal naming the forgery's client-lane URI.
        with pytest.raises(ArtifactNotFound) as by_uri:
            opened.record_of(refusal.model_copy(update={"replay_reference": filed.uri}))
        assert isinstance(by_uri.value, _provenance().RecordNotFiledByRecordWriter), by_uri.value
