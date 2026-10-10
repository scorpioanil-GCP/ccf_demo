"""The admission gate derives its record's reference BEFORE the store holds the record (``D-IMPL-380``, ruling 1 (a)).

Dave, 2026-10-10 05:34 MST (the ``D-IMPL-380`` amendment), verbatim: *"Hash before put in both writers. Compare the
store's answer to that precomputed reference. Do not hash the object again after the store has held it. The test
mutates the dictionary and forces a change into the frozen record. The save is refused, and no audit entry is
written."*

``src/ccf/peering/admission.py::PeeringAdmissionGate._persist_admission_record`` handed the ``AdmissionRecord`` to
the store and only afterwards derived the record's content address from the object, so a store that changed the
record while it held it, filed the changed record and answered the changed record's genuine reference passed the
field-by-field check (``D-IMPL-378`` decision 5): the address the gate compared against was the changed object's.
The Fable seat found it at ``a7e4c2d2`` (F-1) and the coordinator reproduced it: the crossing was admitted and the
``peering_admitted`` verdict named the altered record.

Two attackers, each a store that alters the record inside ``put``, files the altered record through the real store,
and answers honestly for what it filed:

1. **The live mapping.** ``AdmissionRecord`` is frozen, but ``issuance.echo.parameters`` validates to a plain
   ``dict``; the store writes a key into it.
2. **The frozen record itself.** ``object.__setattr__`` bypasses a frozen Pydantic model's guard; the store rewrites
   a field of the record. Freezing the mapping would not stop this one.

For each: the crossing is refused ``AdmissionRecordReferenceMismatch`` (asserted by the class NAME, so a tree
without the ordering fails on its behavior, never on an import), and no ``peering_admitted`` verdict is appended.
Every domain value comes from ``tests/fixtures/banking/*.yaml`` through the admission-record harness (CINV-01).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.peering.admission import AdmissionRecord, AdmittedProduct
from ccf.peering.identity import DetachedJwsIdentityProvider, JsonWebKey
from ccf.products.contract import RegisteredProductClass
from tests.peering.test_admission_record import (  # noqa: F401 — pytest fixtures, used by name
    _build_gate,
    banking_product,
    key_dir,
    product_class,
    provider,
    public_key,
    registry,
    store,
)
from tests.peering.test_admission_record_writer_checks_the_returned_reference import _admit, _admitted_events

#: The refusal the precomputed reference raises, by name.
REFUSAL = "AdmissionRecordReferenceMismatch"


def _alter_the_mapping(record: AdmissionRecord) -> None:
    record.issuance.echo.parameters["injected_by_store"] = "laundered"


def _force_into_the_frozen_record(record: AdmissionRecord) -> None:
    object.__setattr__(record, "peer_id", f"{record.peer_id}-laundered")


#: Each attacker: how the store changes the record it was handed, inside ``put``.
ATTACKERS: dict[str, Callable[[AdmissionRecord], None]] = {
    "the live mapping": _alter_the_mapping,
    "object.__setattr__ on the frozen record": _force_into_the_frozen_record,
}


class _AltersWhileHeld:
    """Alters the record it is handed, files the altered record through ``inner``, answers what it filed."""

    def __init__(self, inner: FileArtifactStore, alter: Callable[[AdmissionRecord], None]) -> None:
        self._inner = inner
        self._alter = alter
        self.as_built: str | None = None
        self.as_altered: str | None = None

    def put(self, authorized: Any, artifact: Any) -> Any:
        record = artifact.artifact
        if isinstance(record, AdmissionRecord):
            self.as_built = content_hash(record)
            self._alter(record)
            self.as_altered = content_hash(record)
        return self._inner.put(authorized, artifact)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.mark.parametrize("attacker", sorted(ATTACKERS))
def test_a_store_that_alters_the_record_while_it_holds_it_is_refused_and_no_verdict_is_written(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
    attacker: str,
) -> None:
    altering = _AltersWhileHeld(store, ATTACKERS[attacker])
    gate = _build_gate(
        provider=provider, public_key=public_key, registry=registry, product_class=product_class, artifact_store=altering
    )
    before = len(_admitted_events(registry))

    outcome = _admit(gate, provider, banking_product())

    assert altering.as_built is not None and altering.as_built != altering.as_altered, (
        f"[{attacker}] the case was not constructed: the store must have changed the record's address"
    )
    events = _admitted_events(registry)
    if isinstance(outcome, AdmittedProduct):
        pytest.fail(
            f"[{attacker}] the crossing was admitted with the record the store altered: the verdict names"
            f" version={events[-1].version if len(events) > before else None}; the record as the gate built it is"
            f" {altering.as_built}, as the store altered it {altering.as_altered}"
        )
    assert any(klass.__name__ == REFUSAL for klass in type(outcome).__mro__), (
        f"[{attacker}] not refused by the precomputed reference ({REFUSAL}): {type(outcome).__name__}: {outcome}"
    )
    assert len(events) == before, f"[{attacker}] a peering_admitted verdict was appended for the altered record"
