# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The admitted product never carries what the store held (``D-IMPL-380``, second round, ruling 2 (a)).

Dave, 2026-10-10 07:39 MST (the ``D-IMPL-380`` amendment), verbatim: *"Each writer gives the store a deep copy made
before the save and keeps its own. The caller and the replay record, including the workflow resume path, get the
untouched copy. The test alters the record and then answers with the original fingerprint. The saved-bytes limit
stays disclosed."*

``src/ccf/peering/admission.py::PeeringAdmissionGate._persist_admission_record`` derives the record's reference before
``put`` (the first round), so a store that alters the record and answers the ALTERED record's reference is refused.
A store that alters the record and answers the record's ORIGINAL reference passes that check, because the
reference is right. At ``ef5d27a4`` the store was handed the gate's own record, whose ``issuance`` is the very
``IssuanceClaims`` instance ``admit`` goes on to return in ``AdmittedProduct.issuance``: the store's alteration
reached the caller (Fable seat 2, F2-2; reproduced by the coordinator).

Two attackers, each a store that alters the record it is handed inside ``put``, files the altered record through
the real store, and answers the reference of the record as it was handed (the original fingerprint):

1. **The live mapping.** ``issuance.echo.parameters`` validates to a plain ``dict``; the store writes a key into it.
2. **The frozen record itself.** ``object.__setattr__`` bypasses a frozen Pydantic model's guard; the store rewrites
   the issuance's nonce.

For each: the crossing is admitted (the reference is right), and ``AdmittedProduct.issuance`` is byte-for-byte the
issuance as the gate built it. Every domain value comes from ``tests/fixtures/banking/*.yaml`` through the
admission-record harness (CINV-01).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
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
from tests.peering.test_admission_record_writer_checks_the_returned_reference import _admit


def _alter_the_mapping(record: AdmissionRecord) -> None:
    record.issuance.echo.parameters["injected_by_store"] = "laundered"


def _force_into_the_frozen_issuance(record: AdmissionRecord) -> None:
    object.__setattr__(record.issuance, "nonce", f"{record.issuance.nonce}-laundered")


#: Each attacker: how the store changes the record it was handed, inside ``put``.
ATTACKERS: dict[str, Callable[[AdmissionRecord], None]] = {
    "the live mapping": _alter_the_mapping,
    "object.__setattr__ on the frozen issuance": _force_into_the_frozen_issuance,
}


class _AltersAndAnswersTheOriginal:
    """Alters the record it is handed, files the altered record, answers the record's reference as handed."""

    def __init__(self, inner: FileArtifactStore, alter: Callable[[AdmissionRecord], None]) -> None:
        self._inner = inner
        self._alter = alter
        self.as_handed: str | None = None
        self.as_altered: str | None = None
        self.issuance_as_handed: bytes | None = None

    def put(self, authorized: Any, artifact: Any) -> Any:
        record = artifact.artifact
        if not isinstance(record, AdmissionRecord):
            return self._inner.put(authorized, artifact)
        self.as_handed = content_hash(record)
        self.issuance_as_handed = canonical_bytes(record.issuance)
        self._alter(record)
        self.as_altered = content_hash(record)
        filed = self._inner.put(authorized, artifact)
        # The original fingerprint: the reference of the record as it was handed, naming what was filed.
        return filed.model_copy(
            update={
                "content_address": self.as_handed,
                "uri": filed.uri.replace(self.as_altered, self.as_handed),
            }
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.mark.parametrize("attacker", sorted(ATTACKERS))
def test_a_store_that_alters_the_record_and_answers_the_original_reference_leaves_the_admitted_issuance_as_built(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
    attacker: str,
) -> None:
    altering = _AltersAndAnswersTheOriginal(store, ATTACKERS[attacker])
    gate = _build_gate(
        provider=provider, public_key=public_key, registry=registry, product_class=product_class, artifact_store=altering
    )

    outcome = _admit(gate, provider, banking_product())

    assert altering.as_handed is not None and altering.as_handed != altering.as_altered, (
        f"[{attacker}] the case was not constructed: the store must have changed the record's address"
    )
    assert isinstance(outcome, AdmittedProduct), (
        f"[{attacker}] the store answered the record's own reference, so the crossing must be admitted:"
        f" {type(outcome).__name__}: {outcome}"
    )
    assert canonical_bytes(outcome.issuance) == altering.issuance_as_handed, (
        f"[{attacker}] AdmittedProduct.issuance carries the store's alteration: the caller got"
        f" {canonical_bytes(outcome.issuance).decode('utf-8')!r}, the issuance as the gate built it is"
        f" {(altering.issuance_as_handed or b'').decode('utf-8')!r}"
    )
